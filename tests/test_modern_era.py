"""Gemessen statt erschlossen: echte 2026-07-28-Anfragen durch die ASGI-App.

`test_protocol_version.py` pinnt die beiden Spec-Revisionen gegen die
SDK-Konstanten. Das ist die schwaechere Form, und sie stand dort auch so
benannt: «dieses Repo baut keine ASGI-App, durch die sich ein `initialize`
schicken liesse». Das war falsch — `mcp.streamable_http_app()` baut genau eine,
und `__main__.py` faehrt sie unter `SWISS_HOUSING_TRANSPORT=streamable-http`
produktiv. Hier laufen deshalb echte Anfragen durch: Statuscode, Aushandlung und
Antwortkoerper sind gemessen, nicht aus Konstantennamen geschlossen.

Was die Messung beim Einbau gefunden hat — und was kein Gate sah:

* Der Server meldete `"version": ""`. Das SDK fuellt nichts nach; sein eigener
  Docstring sagt es: «An unversioned server reports an empty `version`; the SDK
  never substitutes its own.» Spec `2026-07-28` stempelt `serverInfo` in *jedes*
  Resultat — die leere Version ging also auf jeder Antwort mit, nicht bloss
  einmal im Handshake.
* `check_version_sync.py` blieb dabei gruen, und zwar zu Recht: es vergleicht
  die *deklarierten* Versionen (`server.json`, README-Badges) und verbietet
  Literale in `src/`. Was der Server auf dem Draht ankuendigt, hat nie jemand
  gelesen. Die Zusicherung unten schliesst genau diese Luecke.

Zwei Eigenheiten der Messung, beide beim Aufbau ueber den Fuss gefallen:

* Der Host muss `127.0.0.1` sein. Starlettes Vorgabe `testserver` faellt am
  DNS-Rebinding-Schutz des SDK mit HTTP 421 — und 421 sieht wie ein kaputter
  Test aus, obwohl der Schutz genau das Richtige tut.
* Die moderne Aera wird ueber den `MCP-Protocol-Version`-Header betreten. Fehlt
  er, landet die Anfrage auf dem Legacy-Pfad und antwortet ebenfalls mit 200 —
  ein Test ohne `test_ohne_envelope_...` unten koennte also gruen sein, ohne je
  modern gesprochen zu haben.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from mcp.server.mcpserver import MCPServer
from mcp.types.version import LATEST_HANDSHAKE_VERSION, LATEST_MODERN_VERSION
from starlette.testclient import TestClient

from swiss_housing_mcp._version import __homepage__, __summary__, __version__
from swiss_housing_mcp.server import LIST_CACHE_TTL_MS, mcp

# Der Host, unter dem die App ohne 421 antwortet — siehe Modul-Docstring.
BASE_URL = "http://127.0.0.1:8000"

PV = LATEST_MODERN_VERSION

# Die drei `_meta`-Schluessel des Pro-Request-Envelopes. `clientInfo` ist
# optional, `protocolVersion` und `clientCapabilities` sind es nicht — die
# Ladder im SDK weist eine Anfrage ohne sie mit -32602 ab.
PROTOCOL_VERSION_KEY = "io.modelcontextprotocol/protocolVersion"
CLIENT_INFO_KEY = "io.modelcontextprotocol/clientInfo"
CLIENT_CAPABILITIES_KEY = "io.modelcontextprotocol/clientCapabilities"
SERVER_INFO_KEY = "io.modelcontextprotocol/serverInfo"

# Beide Aeren verlangen beide Accept-Typen: der Legacy-Pfad antwortet als SSE,
# der moderne je nach Modus als JSON — wer nur einen schickt, bekommt HTTP 406
# und damit einen Fehlschlag, der nach Aushandlung aussieht.
JSON_UND_SSE = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def envelope(protocol_version: str = PV) -> dict[str, Any]:
    return {
        PROTOCOL_VERSION_KEY: protocol_version,
        CLIENT_INFO_KEY: {"name": "pytest", "version": "0"},
        CLIENT_CAPABILITIES_KEY: {},
    }


@pytest.fixture
def client():
    """Die App des Servers, mit gelaufenem Lifespan.

    `TestClient` als Kontextmanager fuehrt den Lifespan aus. Ohne ihn ist die
    Task-Group des Session-Managers `None`, und *jede* Anfrage stirbt an einem
    `RuntimeError` statt an dem, was sie pruefen sollte.
    """
    with TestClient(mcp.streamable_http_app(), base_url=BASE_URL) as c:
        yield c


def modern_post(
    client: TestClient,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    meta: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
):
    """Eine Anfrage der modernen Aera: Envelope im Koerper, Spiegel im Header.

    Die Ladder vergleicht `MCP-Protocol-Version` und `Mcp-Method` gegen den
    Koerper und weist jede Abweichung ab — die Header sind deshalb aus dem
    Koerper abgeleitet und nicht separat gepflegt.
    """
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": {**(params or {}), "_meta": envelope() if meta is None else meta},
    }
    wire = {"MCP-Protocol-Version": PV, "Mcp-Method": method, **JSON_UND_SSE}
    name = (params or {}).get("name")
    if name is not None:
        wire["Mcp-Name"] = name
    wire.update(headers or {})
    return client.post("/mcp", content=json.dumps(body), headers=wire)


def result_of(response) -> dict[str, Any]:
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "error" not in payload, payload["error"]
    return payload["result"]


# --------------------------------------------------------------------------
# Wird die moderne Aera ueberhaupt betreten?
# --------------------------------------------------------------------------


def test_discover_nennt_genau_die_moderne_revision(client) -> None:
    """`server/discover` gibt es nur modern — der Beleg, dass wir dort sind."""
    result = result_of(modern_post(client, "server/discover"))
    assert result["supportedVersions"] == [PV]


def test_ohne_envelope_antwortet_der_legacy_pfad(client) -> None:
    """Negativkontrolle zur Aera-Frage.

    Ohne `MCP-Protocol-Version`-Header routet das SDK auf den Legacy-Pfad.
    `server/discover` existiert dort nicht — kaeme hier ein Resultat, wuerde
    jede Zusicherung oben auch ohne moderne Aera halten und damit nichts ueber
    sie aussagen.
    """
    response = client.post(
        "/mcp",
        content=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "server/discover"}),
        headers=JSON_UND_SSE,
    )
    body = response.text
    assert '"supportedVersions"' not in body, (
        "server/discover hat ohne modernen Envelope geantwortet — dann belegt "
        "keiner der Tests oben, dass die moderne Aera betreten wurde"
    )


def test_ein_unvollstaendiger_envelope_wird_abgewiesen(client) -> None:
    """Die Ladder greift wirklich; die Envelope-Pflichtfelder sind keine Zierde."""
    ohne_capabilities = {k: v for k, v in envelope().items() if k != CLIENT_CAPABILITIES_KEY}
    response = modern_post(client, "tools/list", meta=ohne_capabilities)
    payload = response.json()
    assert "error" in payload, payload
    assert payload["error"]["code"] == -32602, payload["error"]


def test_ein_header_der_dem_koerper_widerspricht_wird_abgewiesen(client) -> None:
    """Spec 2026-07-28 spiegelt die Route in Header; ein Widerspruch ist ein Fehler."""
    response = modern_post(client, "tools/list", headers={"Mcp-Method": "prompts/list"})
    payload = response.json()
    assert "error" in payload, payload


# --------------------------------------------------------------------------
# Identitaet — der Befund, den erst die Messung sichtbar gemacht hat
# --------------------------------------------------------------------------


def test_der_server_nennt_seine_version_auf_jeder_antwort(client) -> None:
    """Die Luecke, die `check_version_sync.py` nicht sehen konnte.

    Geprueft auf `tools/list` und nicht auf `server/discover`: modern traegt
    *jedes* Resultat den `serverInfo`-Stempel, und eine leere Version ginge auf
    jeder Antwort mit.
    """
    result = result_of(modern_post(client, "tools/list"))
    server_info = result["_meta"][SERVER_INFO_KEY]
    assert server_info["version"] == __version__, (
        f"der Server kuendigt {server_info.get('version')!r} an, das Paket steht "
        f"auf {__version__!r}"
    )
    assert server_info["version"], (
        "leere Version: `MCPServer(...)` bekam kein `version=` — das SDK fuellt "
        "nichts nach, und kein bestehendes Gate liest die Draht-Ankuendigung"
    )


def test_ein_server_ohne_identitaet_meldet_eine_leere_version() -> None:
    """Negativkontrolle: gleiches SDK, gleicher Pfad, keine Argumente.

    Faengt den Tag ab, an dem das SDK doch etwas nachfuellte — dann pruefte der
    Test oben naemlich nicht mehr, dass *wir* die Version setzen.
    """
    with TestClient(MCPServer("kontrolle").streamable_http_app(), base_url=BASE_URL) as c:
        result = result_of(modern_post(c, "tools/list"))

    assert result["_meta"][SERVER_INFO_KEY]["version"] == ""


def test_die_identitaet_stammt_aus_den_paket_metadaten(client) -> None:
    """`description` und `websiteUrl` sind keine zweite Kopie.

    Beide stehen in `pyproject.toml` und kommen von dort ueber die
    Distributions-Metadaten. Ein Literal in `src/` waere derselbe Drift-Anfang
    wie eine hartkodierte Version — nur ohne Gate, das ihn faengt.
    """
    result = result_of(modern_post(client, "server/discover"))
    server_info = result["_meta"][SERVER_INFO_KEY]
    assert server_info["description"] == __summary__
    assert server_info["websiteUrl"] == __homepage__
    assert server_info["name"] == "swiss-housing-mcp"
    assert server_info["title"]


def test_discover_traegt_die_bedienungsanleitung(client) -> None:
    """Modern gibt es keinen Handshake — `discover` ist der einzige Kanal.

    Ein Client, der die Spec 2026-07-28 spricht, sieht `instructions` nirgends
    sonst. Ohne sie bekaeme er neun Werkzeuge und keinen Hinweis darauf, dass
    die Dump-Tools beim ersten Aufruf pro Kanton langsam sind.
    """
    result = result_of(modern_post(client, "server/discover"))
    instructions = result.get("instructions") or ""
    assert "EGID" in instructions, instructions
    assert "dump" in instructions.lower(), instructions


# --------------------------------------------------------------------------
# Frischehinweise und Werkzeuge, auf der modernen Leitung statt in-process
# --------------------------------------------------------------------------


def test_die_frischehinweise_stehen_auf_der_leitung(client) -> None:
    """`test_cache_hints.py` misst dasselbe ueber einen In-Process-Client.
    Hier steht es auf dem Draht, samt `cacheScope`, den ein Proxy liest."""
    for method in ("tools/list", "server/discover"):
        result = result_of(modern_post(client, method))
        assert result["ttlMs"] == LIST_CACHE_TTL_MS, (method, result.get("ttlMs"))
        assert result["cacheScope"] == "public", (method, result.get("cacheScope"))


def test_ein_werkzeugaufruf_laeuft_ueber_den_modernen_envelope(client) -> None:
    """Der Vollpfad: Envelope rein, Werkzeugergebnis raus.

    `dump_status` gewaehlt, weil es als einziges Werkzeug ohne Netz auskommt —
    ein Live-Aufruf wuerde hier die Aushandlung an der Erreichbarkeit der
    Quelle messen.
    """
    result = result_of(modern_post(client, "tools/call", {"name": "dump_status", "arguments": {}}))
    assert result.get("isError") is not True, result
    payload = json.loads(result["content"][0]["text"])
    assert payload["provenance"] == "cached"
    assert payload["dumps"]


def test_alle_werkzeuge_sind_modern_sichtbar(client) -> None:
    result = result_of(modern_post(client, "tools/list"))
    namen = {tool["name"] for tool in result["tools"]}
    assert "dump_status" in namen
    assert "new_construction" in namen
    assert len(namen) == 9, sorted(namen)


# --------------------------------------------------------------------------
# Die Handshake-Aera, ebenfalls gemessen
# --------------------------------------------------------------------------


def handshake(client: TestClient, requested: str) -> dict[str, Any]:
    """Ein `initialize` ueber denselben Endpunkt, ohne Envelope."""
    response = client.post(
        "/mcp",
        content=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": requested,
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "0"},
                },
            }
        ),
        headers=JSON_UND_SSE,
    )
    assert response.status_code == 200, response.text
    text = response.text
    # Der Legacy-Pfad antwortet als SSE, sofern nicht JSON-Modus erzwungen ist.
    for line in text.splitlines():
        if line.startswith("data: "):
            text = line[len("data: ") :]
            break
    return json.loads(text)["result"]


@pytest.mark.parametrize("requested", ["2024-11-05", "2025-06-18", LATEST_HANDSHAKE_VERSION])
def test_der_handshake_antwortet_mit_der_angefragten_revision(client, requested) -> None:
    """Was die README-Tabelle behauptet, hier gemessen statt zitiert."""
    assert handshake(client, requested)["protocolVersion"] == requested


def test_der_handshake_deckelt_statt_die_moderne_revision_zu_nennen(client) -> None:
    """Die lasttragende Zusicherung der Handshake-Zeile.

    Ein Client, der etwas Neueres verlangt, bekommt die Obergrenze — nicht
    `2026-07-28`. Die Aeren sind getrennt: die moderne erreicht man ueber den
    Envelope, nie ueber `initialize`.
    """
    for requested in (PV, "2099-01-01"):
        negotiated = handshake(client, requested)["protocolVersion"]
        assert negotiated == LATEST_HANDSHAKE_VERSION, (requested, negotiated)
        assert negotiated != PV


def test_der_handshake_nennt_dieselbe_version_wie_die_moderne_aera(client) -> None:
    """Derselbe Befund, andere Aera: `serverInfo` traegt beide Male die Version."""
    assert handshake(client, LATEST_HANDSHAKE_VERSION)["serverInfo"]["version"] == __version__
