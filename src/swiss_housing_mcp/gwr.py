"""Data access layer for the GWR/RegBL (Federal Register of Buildings and Dwellings).

Architecture B (Hybrid: Dump-first, API-fallback), verified live 2026-07-24:
- Cantonal SQLite dumps from public.madd.bfs.admin.ch (refreshed daily ~05:30 CET)
  are the primary source for aggregations and spatial queries.
- api3.geo.admin.ch (find / identify / SearchServer) serves single-entity lookups
  and address geocoding. No authentication required for either path.

Known findings (live probe 2026-07-24):
- geo.admin.ch returns HTTP 200 with an empty ``results`` array for unknown EGIDs
  — an empty array is a soft "not found", NOT an upstream error.
- The public dump ZIP ships a ready-made ``data.sqlite`` (tables: building,
  entrance, dwelling, code, _metadata). No CSV parsing required.
- Coordinates are LV95 (EPSG:2056): GKODE (east, ~2'480'000-2'840'000),
  GKODN (north, ~1'070'000-1'300'000).
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

import httpx

MADD_BASE = "https://public.madd.bfs.admin.ch"
GEOADMIN_BASE = "https://api3.geo.admin.ch/rest/services/api"
GWR_LAYER = "ch.bfs.gebaeude_wohnungs_register"

CACHE_DIR = Path(
    os.environ.get("SWISS_HOUSING_CACHE", Path.home() / ".cache" / "swiss-housing-mcp")
)
DUMP_TTL_HOURS = float(os.environ.get("SWISS_HOUSING_DUMP_TTL_HOURS", "24"))

# Cantons with a public dump (lowercase two-letter codes as used by MADD).
CANTONS = {
    "zh",
    "be",
    "lu",
    "ur",
    "sz",
    "ow",
    "nw",
    "gl",
    "zg",
    "fr",
    "so",
    "bs",
    "bl",
    "sh",
    "ar",
    "ai",
    "sg",
    "gr",
    "ag",
    "tg",
    "ti",
    "vd",
    "vs",
    "ne",
    "ge",
    "ju",
}


async def fetch_with_retry(http: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    """GET with exponential backoff: 3 retries at 2s/4s/8s. 4xx (except 429) not retried."""
    last_error: Exception | None = None
    for attempt in range(4):
        if attempt > 0:
            await asyncio.sleep(2**attempt)
        try:
            resp = await http.get(url, **kwargs)
            resp.raise_for_status()
            return resp
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            last_error = exc
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status is not None and 400 <= status < 500 and status != 429:
                raise
    assert last_error is not None
    raise RuntimeError(f"Upstream unreachable after retries: {last_error}")


@dataclass
class DumpInfo:
    canton: str
    path: Path
    fetched_at: float

    @property
    def age_hours(self) -> float:
        return (time.time() - self.fetched_at) / 3600

    @property
    def stale(self) -> bool:
        return self.age_hours > DUMP_TTL_HOURS


def _write_and_extract(zip_path: Path, content: bytes, sqlite_path: Path) -> None:
    """Blocking IO isolated for asyncio.to_thread: write ZIP, extract data.sqlite."""
    zip_path.write_bytes(content)
    with (
        zipfile.ZipFile(zip_path) as zf,
        zf.open("data.sqlite") as src,
        open(sqlite_path, "wb") as dst,
    ):
        while chunk := src.read(1 << 20):
            dst.write(chunk)
    zip_path.unlink(missing_ok=True)


class GwrStore:
    """Manages cantonal SQLite dumps: download, cache with TTL, query."""

    def __init__(self) -> None:
        self._dumps: dict[str, DumpInfo] = {}
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _sqlite_path(self, canton: str) -> Path:
        return CACHE_DIR / f"gwr_{canton}.sqlite"

    async def ensure_dump(self, canton: str, http: httpx.AsyncClient) -> DumpInfo:
        """Return a fresh dump for the canton, downloading if missing or stale."""
        canton = canton.lower()
        if canton not in CANTONS:
            raise ValueError(f"Unknown canton code: {canton!r}. Expected one of {sorted(CANTONS)}")

        cached = self._dumps.get(canton)
        path = self._sqlite_path(canton)
        if cached is None and path.exists():
            cached = DumpInfo(canton, path, path.stat().st_mtime)
            self._dumps[canton] = cached
        if cached is not None and not cached.stale:
            return cached

        zip_path = CACHE_DIR / f"{canton}.zip"
        resp = await fetch_with_retry(http, f"{MADD_BASE}/{canton}.zip", timeout=300.0)
        await asyncio.to_thread(_write_and_extract, zip_path, resp.content, path)

        info = DumpInfo(canton, path, time.time())
        self._dumps[canton] = info
        return info

    def query(self, canton: str, sql: str, params: tuple = ()) -> list[dict]:
        """Run a read-only query against the cached cantonal dump."""
        path = self._sqlite_path(canton.lower())
        if not path.exists():
            raise FileNotFoundError(f"No cached dump for canton {canton!r}; call ensure_dump first")
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in con.execute(sql, params)]
        finally:
            con.close()

    def status(self) -> list[dict]:
        out = []
        for canton in sorted(CANTONS):
            path = self._sqlite_path(canton)
            if path.exists():
                age = (time.time() - path.stat().st_mtime) / 3600
                out.append(
                    {
                        "canton": canton,
                        "cached": True,
                        "age_hours": round(age, 1),
                        "stale": age > DUMP_TTL_HOURS,
                        "size_mb": round(path.stat().st_size / 1e6, 1),
                    }
                )
            else:
                out.append({"canton": canton, "cached": False})
        return out


async def geoadmin_find_egid(http: httpx.AsyncClient, egid: int) -> dict | None:
    """Look up a single building by EGID via the geo.admin.ch find API.

    Returns None for unknown EGIDs (upstream answers 200 + empty results — soft error).
    """
    url = (
        f"{GEOADMIN_BASE}/MapServer/find"
        f"?layer={GWR_LAYER}&searchField=egid&searchText={egid}&returnGeometry=true&sr=2056"
    )
    resp = await fetch_with_retry(http, url, timeout=20.0)
    results = resp.json().get("results", [])
    return results[0] if results else None


async def geoadmin_geocode(http: httpx.AsyncClient, address: str, limit: int = 5) -> list[dict]:
    """Geocode an address via SearchServer. featureId in results is '{EGID}_{EDID}'."""
    url = (
        f"{GEOADMIN_BASE}/SearchServer"
        f"?searchText={httpx.QueryParams({'q': address})['q']}"
        f"&type=locations&origins=address&limit={limit}&sr=2056"
    )
    resp = await fetch_with_retry(http, url, timeout=20.0)
    return resp.json().get("results", [])
