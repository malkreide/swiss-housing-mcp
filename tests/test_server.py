"""Tests for swiss-housing-mcp.

Run from project root: PYTHONPATH=src pytest tests/ -m "not live"
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime, parsedate_to_datetime

import httpx
import pytest
import respx

from swiss_housing_mcp import gwr

FIND_URL = f"{gwr.GEOADMIN_BASE}/MapServer/find"
SEARCH_URL = f"{gwr.GEOADMIN_BASE}/SearchServer"

BUILDING_PAYLOAD = {
    "results": [
        {
            "attributes": {
                "egid": "302031642",
                "ggdenr": 261,
                "ggdename": "Zürich",
                "gdekt": "ZH",
                "strname_deinr": "Seilergraben 76",
                "gstat": 1004,
                "gkat": 1080,
                "gbauj": 1999,
            }
        }
    ]
}


# --- 1. Happy path -----------------------------------------------------------


@respx.mock
async def test_find_egid_happy_path():
    respx.get(url__startswith=FIND_URL).mock(
        return_value=httpx.Response(200, json=BUILDING_PAYLOAD)
    )
    async with httpx.AsyncClient() as http:
        result = await gwr.geoadmin_find_egid(http, 302031642)
    assert result is not None
    assert result["attributes"]["ggdename"] == "Zürich"


@respx.mock
async def test_geocode_happy_path():
    respx.get(url__startswith=SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "attrs": {
                            "label": "Seilergraben 76 8001 Zürich",
                            "featureId": "302031642_0",
                            "y": 2683531.0,
                            "x": 1247914.5,
                        }
                    }
                ]
            },
        )
    )
    async with httpx.AsyncClient() as http:
        results = await gwr.geoadmin_geocode(http, "Seilergraben 76 Zürich")
    assert results[0]["attrs"]["featureId"] == "302031642_0"


# --- 2. Soft error: empty results is "not found", not an exception -----------


@respx.mock
async def test_find_egid_soft_error_empty_results():
    """Known finding 2026-07-24: unknown EGID → HTTP 200 + empty array."""
    respx.get(url__startswith=FIND_URL).mock(return_value=httpx.Response(200, json={"results": []}))
    async with httpx.AsyncClient() as http:
        result = await gwr.geoadmin_find_egid(http, 999999999)
    assert result is None


# --- 3. Retry on 503 ---------------------------------------------------------


@respx.mock
async def test_retry_on_503_then_success(monkeypatch):
    monkeypatch.setattr(gwr, "_sleep", _instant_sleep)
    route = respx.get(url__startswith=FIND_URL)
    route.side_effect = [
        httpx.Response(503),
        httpx.Response(200, json=BUILDING_PAYLOAD),
    ]
    async with httpx.AsyncClient() as http:
        result = await gwr.geoadmin_find_egid(http, 302031642)
    assert result is not None
    assert route.call_count == 2


@respx.mock
async def test_no_retry_on_404(monkeypatch):
    monkeypatch.setattr(gwr, "_sleep", _instant_sleep)
    route = respx.get(url__startswith=FIND_URL).mock(return_value=httpx.Response(404))
    async with httpx.AsyncClient() as http:
        with pytest.raises(httpx.HTTPStatusError):
            await gwr.geoadmin_find_egid(http, 1)
    assert route.call_count == 1


# --- 4. Timeout / network error → clean error, no stacktrace soup ------------


@respx.mock
async def test_network_error_surfaces_the_original_exception(monkeypatch):
    """The transport error travels out unwrapped, with its type intact.

    This test used to assert ``RuntimeError, match="Upstream unreachable"`` and
    so pinned the very defect it was meant to cover. ``httpx.ConnectError``,
    ``ConnectTimeout`` and ``ReadTimeout`` all carry an EMPTY ``str()`` in the
    real world — the wrapper interpolated that emptiness and produced a message
    that stopped at the colon, naming neither the failure mode nor the host.
    The mock passes ``"boom"`` here, which is exactly why asserting on the
    message was misleading: it looked informative in the test and was blank in
    production.
    """
    monkeypatch.setattr(gwr, "_sleep", _instant_sleep)
    respx.get(url__startswith=FIND_URL).mock(side_effect=httpx.ConnectError("boom"))
    async with httpx.AsyncClient() as http:
        with pytest.raises(httpx.ConnectError):
            await gwr.geoadmin_find_egid(http, 302031642)


@respx.mock
async def test_empty_str_error_still_names_its_type(monkeypatch):
    """The case the old wrapper turned into a message ending at the colon."""
    monkeypatch.setattr(gwr, "_sleep", _instant_sleep)
    respx.get(url__startswith=FIND_URL).mock(side_effect=httpx.ConnectTimeout(""))
    async with httpx.AsyncClient() as http:
        with pytest.raises(httpx.ConnectTimeout) as raised:
            await gwr.geoadmin_find_egid(http, 302031642)
    assert str(raised.value) == ""
    assert type(raised.value).__name__ == "ConnectTimeout"


# --- 4b. Retry-After, jitter and the cap -------------------------------------


def _status_error(headers: dict[str, str]) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.invalid/")
    return httpx.HTTPStatusError(
        "",
        request=request,
        response=httpx.Response(429, headers=headers, request=request),
    )


def test_retry_after_reads_both_rfc9110_forms():
    def resp(status: int, headers: dict[str, str]) -> httpx.Response:
        request = httpx.Request("GET", "https://example.invalid/")
        return httpx.Response(status, headers=headers, request=request)

    assert gwr.parse_retry_after(resp(429, {"Retry-After": "120"})) == 120.0

    later = format_datetime(datetime.now(UTC) + timedelta(seconds=90))
    seconds = gwr.parse_retry_after(resp(503, {"Retry-After": later}))
    assert seconds is not None and 80 < seconds <= 90

    # A date in the past means "now", never a negative wait.
    past = "Wed, 21 Oct 2020 07:28:00 GMT"
    assert gwr.parse_retry_after(resp(503, {"Retry-After": past})) == 0.0

    # Unparseable falls back to the curve — it must not crash on the error path.
    assert gwr.parse_retry_after(resp(429, {"Retry-After": "bald"})) is None
    assert gwr.parse_retry_after(resp(429, {})) is None

    # 500 does not carry a meaningful Retry-After.
    assert gwr.parse_retry_after(resp(500, {"Retry-After": "120"})) is None
    assert gwr.parse_retry_after(None) is None


def test_backoff_is_jittered_and_capped_after_jittering():
    delays = {gwr.compute_delay(3, None) for _ in range(300)}
    # attempt 3 -> 2 * 2**2 = 8s, spread into [0.5x, 1.5x]
    assert len(delays) > 1, "a deterministic ladder synchronises every client"
    assert min(delays) >= 4.0
    assert max(delays) <= 12.0

    # The cap is applied AFTER the jitter. Capping first and then multiplying by
    # up to 1.5 would land at 30s, and the constant would claim a ceiling it
    # does not hold.
    deep = {gwr.compute_delay(9, None) for _ in range(200)}
    assert max(deep) <= gwr.RETRY_MAX_DELAY

    hinted = _status_error({"Retry-After": "600"})
    assert {gwr.compute_delay(1, hinted) for _ in range(100)} == {gwr.RETRY_MAX_DELAY}


def test_retry_after_jitter_is_one_sided():
    """The source said when. Later is polite; earlier ignores the value read."""
    delays = {gwr.compute_delay(1, _status_error({"Retry-After": "4"})) for _ in range(300)}
    assert min(delays) >= 4.0, "never earlier than the source asked for"
    assert max(delays) <= 5.0  # 4 * 1.25


# --- 5. Store validation -----------------------------------------------------


async def test_unknown_canton_rejected():
    store = gwr.GwrStore()
    async with httpx.AsyncClient() as http:
        with pytest.raises(ValueError, match="Unknown canton"):
            await store.ensure_dump("xx", http)


# --- Live tests (excluded from CI) -------------------------------------------


@pytest.mark.live
async def test_live_find_egid():
    async with httpx.AsyncClient() as http:
        result = await gwr.geoadmin_find_egid(http, 302031642)
    assert result is not None
    assert result["attributes"]["gdekt"] == "ZH"


@pytest.mark.live
async def test_live_geocode():
    async with httpx.AsyncClient() as http:
        results = await gwr.geoadmin_geocode(http, "Seilergraben 76 Zürich")
    assert any("_" in str(r.get("attrs", {}).get("featureId", "")) for r in results)


# Schwelle fuer die Frische des Dumps. NICHT 24 h, und das ist gemessen:
# Der Nightly-Cron steht auf `29 3 * * *` (03:29 UTC), die Quelle aktualisiert
# gegen 04:03 UTC — der Lauf faellt also 35 Minuten VOR die Aktualisierung, und
# der neueste Dump ist zur Testzeit schon 23.4 h alt. Eine 24-h-Schwelle waere
# damit fast jede Nacht rot, ohne dass irgendetwas driftet: der Test misst dann
# den Zeitpunkt seines eigenen Laufs, nicht den Vertrag mit der Quelle.
#
# 72 h laesst einen ausgefallenen Tag durch und schlaegt an, wenn die Quelle
# mehrere Tage steht. Die Zahl stuetzt sich auf EINE Messung des
# Aktualisierungszeitpunkts (18.9.2026, 04:03:42 UTC); wie stark er schwankt,
# ist unbekannt. Wer sie enger zieht, sollte das vorher nachmessen.
DUMP_MAX_AGE_HOURS = 72


@pytest.mark.live
async def test_live_dump_quelle_antwortet_und_ist_frisch():
    """Die zweite Quelle des Servers — bis hierhin von keinem Live-Test beruehrt.

    Die beiden Tests oben pruefen `api3.geo.admin.ch`. Der Dump kommt von
    `public.madd.bfs.admin.ch`, und genau dort sass am 3.8.2026 die Drift, die
    vier von sechs Datensaetzen kaputtmachte, waehrend alle Unit-Tests gruen
    blieben. Der naechtliche Waechter nannte diese Quelle in seinem Issue-Text,
    pruefte sie aber nicht.

    `HEAD` statt `GET`: der Zuercher Dump wiegt 116 MiB (gemessen 121'664'088
    Bytes am 18.9.2026). Nichts davon muss geladen werden, um zu sehen, ob die
    Quelle noch dieselbe Zusage macht.

    **Was dieser Test faengt:** Host weg, Pfad umbenannt, 404, TLS- oder
    DNS-Fehler, eine HTML-Fehlerseite unter 200, und eine Quelle, die zwar
    antwortet, aber seit Tagen nicht mehr aktualisiert.

    **Was er NICHT faengt:** eine Drift *innerhalb* des Archivs — genau den Fall
    vom 3.8.2026, also eine geaenderte Schreibweise einer Kopfzeile oder
    Spalte. Dafuer braeuchte es einen echten Download samt Entpacken, und das
    ist eine eigene Abwaegung. Dieser Test ist eine Erreichbarkeits- und
    Frischewache, keine Schemawache; wer ihn fuer mehr haelt, hat dieselbe
    Luecke wie vorher, nur mit einem gruenen Haken darueber.

    Geprueft wird `zh` stellvertretend: der Anker-Kanton des Servers. Alle 26
    zu pruefen hiesse 26 HEAD-Anfragen pro Nacht fuer dieselbe Aussage.

    **Wird dieser Test rot mit 403, heisst das «Pfad weg», nicht «gesperrt».**
    Die Quelle ist ein S3-artiger Bucket: ein fehlender Schluessel beantwortet
    sich mit `403 AccessDenied`, nicht mit 404 (gemessen am 18.9.2026 mit einem
    erfundenen Dateinamen). Das ist genau die Verwechslung, vor der CLAUDE.md
    unter «ein 403 ist gar keine Auskunft» warnt — nur andersherum: Hier HAT die
    Quelle geantwortet, und die Antwort lautet, dass es die Datei nicht gibt.
    Wer den Status fuer eine Sperre haelt, sucht ein Zugangsproblem, das keines
    ist.
    """
    url = f"{gwr.MADD_BASE}/zh.zip"
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http:
        resp = await http.head(url)

    assert resp.status_code == 200, f"{url} antwortete mit HTTP {resp.status_code}"

    content_type = resp.headers.get("content-type", "")
    assert "zip" in content_type.lower(), (
        f"{url} liefert {content_type!r} statt eines ZIP — eine Fehlerseite unter 200?"
    )

    # Untergrenze weit unter dem gemessenen Wert: Sie soll eine Fehlerseite
    # ausschliessen, nicht die Groesse des Dumps festschreiben.
    length = int(resp.headers.get("content-length", "0"))
    assert length > 1_000_000, f"{url} meldet nur {length} Bytes — das ist kein Dump"

    last_modified = resp.headers.get("last-modified")
    assert last_modified, f"{url} nennt kein `last-modified` — Frische nicht pruefbar"
    stand = parsedate_to_datetime(last_modified)
    alter = datetime.now(UTC) - stand
    assert alter <= timedelta(hours=DUMP_MAX_AGE_HOURS), (
        f"{url} ist seit {alter.total_seconds() / 3600:.1f} h unveraendert "
        f"(Stand {stand.isoformat()}). Die Quelle aktualisiert normalerweise "
        "taeglich; steht sie, liefert der Server veraltete Zahlen, ohne dass "
        "irgendein Aufruf scheitert."
    )


async def _instant_sleep(_seconds: float) -> None:
    return None


# --- Die Naht, und warum sie nicht `asyncio.sleep` ist -----------------------


def test_der_retry_geht_ueber_den_alias():
    """Sonst patchen die Tests eine Naht, die der Code gar nicht benutzt.

    Umgeht das Modul den Alias, bleibt der Patch wirkungslos und die Suite
    wartet die echte Backoff-Leiter ab. Kein Test faellt dabei — sie wird nur
    um ein Vielfaches langsamer, und eine laengere Laufzeit ist kein Signal,
    das jemand liest. Diese Zusicherung macht daraus einen Fehlschlag.
    """
    quelle = inspect.getsource(gwr)
    assert "await _sleep(" in quelle, "der Retry ruft den Modul-Alias nicht mehr auf"
    assert "await asyncio.sleep(" not in quelle, "der Retry umgeht den Alias"
