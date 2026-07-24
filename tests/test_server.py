"""Tests for swiss-housing-mcp.

Run from project root: PYTHONPATH=src pytest tests/ -m "not live"
"""

from __future__ import annotations

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
async def test_network_error_raises_runtime_error(monkeypatch):
    monkeypatch.setattr(gwr.asyncio, "sleep", _instant_sleep)
    respx.get(url__startswith=FIND_URL).mock(side_effect=httpx.ConnectError("boom"))
    async with httpx.AsyncClient() as http:
        with pytest.raises(RuntimeError, match="Upstream unreachable"):
            await gwr.geoadmin_find_egid(http, 302031642)


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
