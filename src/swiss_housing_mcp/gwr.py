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
import random
import sqlite3
import time
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit

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


# --- Retry policy ------------------------------------------------------------
# Three questions: *what* is retried, *how fast*, and *how long*. The first is
# settled in `fetch_with_retry` (4xx except 429 fails fast); these settle the
# other two. Adopted from the mcp-data-source-probe reference template.

RETRY_ATTEMPTS = 4
RETRY_BASE_DELAY = 2.0  # ladder before jitter: 2, 4, 8

# Ceiling on the WHOLE call — every attempt and every wait together. An attempt
# count is not a bound: four attempts against an upstream that takes 30s to time
# out is two minutes inside one tool call, and the number never says so. The
# anchor is measured, not guessed: the Python MCP SDK ships
# MCP_DEFAULT_TIMEOUT = 30.0, so 25s leaves headroom for framing and parsing.
RETRY_TOTAL_BUDGET = 25.0

# Ceiling for a single wait. Bounds the exponential ladder, and bounds a
# `Retry-After` the source may send but we are not obliged to sit through.
RETRY_MAX_DELAY = 20.0

# Jitter spread. Without it every client that hit the same outage retries in
# lockstep, and the load returns as a wave exactly when the source recovers.
RETRY_JITTER_SPREAD = 0.5  # exponential delays land in [0.5x, 1.5x]

# On a `Retry-After`, deliberately one-sided: the source said when to come back,
# so later is fine and earlier is not.
RETRY_AFTER_JITTER = 0.25  # lands in [1.0x, 1.25x]

# Statuses that carry a meaningful `Retry-After` (RFC 9110 §10.2.3).
RETRY_AFTER_STATUSES = frozenset({429, 503})


class UpstreamUnavailableError(Exception):
    """No request was attempted — the budget was gone before the first try.

    A named type rather than ``RuntimeError``: a caller can branch on this, and
    cannot tell a bare ``RuntimeError`` apart from a bug in this server's own
    code. Raised only when there is no upstream exception to re-raise.
    """


def parse_retry_after(resp: httpx.Response | None) -> float | None:
    """Seconds to wait per the response's ``Retry-After``, or ``None``.

    RFC 9110 §10.2.3 allows two forms — delta-seconds (``120``) and an HTTP-date
    (``Wed, 21 Oct 2026 07:28:00 GMT``). Both appear in the wild, so both are
    read. Anything unparseable yields ``None`` and the caller falls back to its
    own curve: a malformed header must not become a crash on the error path,
    which is the one path already going badly.
    """
    if resp is None or resp.status_code not in RETRY_AFTER_STATUSES:
        return None
    raw = (resp.headers.get("retry-after") or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        return float(raw)
    try:
        when = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:  # RFC 9110 dates are GMT; a naive one means UTC
        when = when.replace(tzinfo=UTC)
    return max(0.0, (when - datetime.now(UTC)).total_seconds())


def compute_delay(attempt: int, last_error: Exception | None) -> float:
    """Seconds to wait before ``attempt`` (1-based for the first retry).

    The source's own answer beats our guess: a ``Retry-After`` on a 429 or 503
    wins over the exponential curve. Everything is spread, then capped.

    The cap wraps the jitter and not the other way round. ``min(cap, base) *
    jitter`` and ``min(cap, base * jitter)`` both contain a cap and a jitter;
    only the second is bounded — a value capped at 20s and then multiplied by
    up to 1.5 lands at 30s.
    """
    hinted = parse_retry_after(getattr(last_error, "response", None))
    if hinted is not None:
        return min(
            hinted * (1.0 + random.random() * RETRY_AFTER_JITTER),
            RETRY_MAX_DELAY,
        )
    return min(
        RETRY_BASE_DELAY
        * 2 ** (attempt - 1)
        * (1.0 - RETRY_JITTER_SPREAD + random.random() * 2 * RETRY_JITTER_SPREAD),
        RETRY_MAX_DELAY,
    )


async def fetch_with_retry(http: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    """GET with jittered backoff, ``Retry-After`` and a wall-clock budget.

    Retries 5xx and 429 and network errors; 4xx except 429 fails fast.

    Raises the last upstream exception unwrapped — ``httpx.HTTPStatusError``,
    ``httpx.RequestError`` or ``TimeoutError``. Callers branch on the type and
    read ``.response`` where it exists; a wrapper takes both away, and for the
    three errors an outage actually produces (``ConnectTimeout``,
    ``ReadTimeout``, ``ConnectError``) it also interpolates an empty ``str()``.
    """
    deadline = time.monotonic() + RETRY_TOTAL_BUDGET
    last_error: Exception | None = None

    for attempt in range(RETRY_ATTEMPTS):
        if attempt > 0:
            delay = compute_delay(attempt, last_error)
            # A wait that outlasts the budget is a wait for nobody: the caller
            # has given up by the time it ends. Stop instead of sleeping.
            if delay >= deadline - time.monotonic():
                break
            await asyncio.sleep(delay)

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            # httpx bounds each operation and its read timeout restarts with
            # every chunk — a slowly trickling response can outlast the budget
            # without a single read expiring. `asyncio.timeout` is the
            # wall-clock deadline the budget actually promises.
            async with asyncio.timeout(remaining):
                resp = await http.get(url, **kwargs)
                resp.raise_for_status()
                return resp
        except TimeoutError as exc:  # the budget is gone, not just this try
            last_error = exc
            break
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            last_error = exc
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status is not None and 400 <= status < 500 and status != 429:
                raise

    if last_error is None:
        raise UpstreamUnavailableError(
            f"no attempt made: the {RETRY_TOTAL_BUDGET:g}s budget was already "
            f"spent (host={urlsplit(url).hostname})"
        )
    raise last_error


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
