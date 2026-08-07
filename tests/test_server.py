"""Tests for swiss-housing-mcp.

Run from project root: PYTHONPATH=src pytest tests/ -m "not live"
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

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
                    {"attrs": {"label": "Seilergraben 76 8001 Zürich",
                               "featureId": "302031642_0", "y": 2683531.0, "x": 1247914.5}}
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
    respx.get(url__startswith=FIND_URL).mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    async with httpx.AsyncClient() as http:
        result = await gwr.geoadmin_find_egid(http, 999999999)
    assert result is None


# --- 3. Retry on 503 ---------------------------------------------------------


@respx.mock
async def test_retry_on_503_then_success(monkeypatch):
    monkeypatch.setattr(gwr.asyncio, "sleep", _instant_sleep)
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
    monkeypatch.setattr(gwr.asyncio, "sleep", _instant_sleep)
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
    monkeypatch.setattr(gwr.asyncio, "sleep", _instant_sleep)
    respx.get(url__startswith=FIND_URL).mock(side_effect=httpx.ConnectError("boom"))
    async with httpx.AsyncClient() as http:
        with pytest.raises(httpx.ConnectError):
            await gwr.geoadmin_find_egid(http, 302031642)


@respx.mock
async def test_empty_str_error_still_names_its_type(monkeypatch):
    """The case the old wrapper turned into a message ending at the colon."""
    monkeypatch.setattr(gwr.asyncio, "sleep", _instant_sleep)
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


async def _instant_sleep(_seconds: float) -> None:
    return None
