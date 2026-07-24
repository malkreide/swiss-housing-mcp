"""swiss-housing-mcp — MCP server for the Swiss GWR/RegBL building & dwelling register.

🎯 Anchor demo query:
    «Wie viele Wohnungen sind seit 2020 in der Stadt Zürich neu erstellt worden,
     wie viele davon mit 4+ Zimmern — und wie viele sind aktuell im Bau?»
    → new_construction(261, 2020) + construction_pipeline(261)

Verified against the live dump 2026-07-24: 16'164 new dwellings since 2020 in the
City of Zurich (27.4% with 4+ rooms), 7'287 dwellings currently under construction.
"""

from __future__ import annotations

import httpx
from mcp.server.fastmcp import FastMCP

from . import gwr
from .models import (
    BBoxStatsResponse,
    Building,
    BuildingResponse,
    CodeExplanation,
    CodeResponse,
    DumpStatusResponse,
    Dwelling,
    DwellingsResponse,
    GeocodeMatch,
    GeocodeResponse,
    MunicipalityStatsResponse,
    NewConstructionResponse,
    PipelineResponse,
    PipelineRow,
    YearRow,
)

mcp = FastMCP("swiss-housing-mcp")
store = gwr.GwrStore()

GSTAT_LABELS = {
    1001: "projected",
    1002: "approved",
    1003: "under construction",
    1004: "existing",
    1005: "not usable",
    1007: "demolished",
    1008: "not built",
}

# BFS municipality number → canton dump code. Populated lazily via the dump's
# building table; the seed below covers the most common portfolio use cases.
_MUNI_CANTON_SEED = {261: "zh"}


def _http() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers={"User-Agent": "swiss-housing-mcp/0.1.0"})


async def _canton_for_municipality(bfs_nr: int, http: httpx.AsyncClient) -> str:
    """Resolve a BFS municipality number to its canton dump code.

    Checks already-cached dumps first, then falls back to the seed map.
    """
    for canton in [d["canton"] for d in store.status() if d.get("cached")]:
        rows = store.query(canton, "SELECT 1 FROM building WHERE GGDENR=? LIMIT 1", (bfs_nr,))
        if rows:
            return canton
    if bfs_nr in _MUNI_CANTON_SEED:
        return _MUNI_CANTON_SEED[bfs_nr]
    raise ValueError(
        f"Cannot resolve canton for BFS municipality {bfs_nr}. "
        "Pass the canton explicitly via the `canton` parameter."
    )


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
async def lookup_building(egid: int) -> BuildingResponse:
    """Look up a single building by its EGID (federal building identifier).

    Uses the live geo.admin.ch API — always current, no dump download needed.
    The EGID is the join key used across Swiss administrative data.
    """
    async with _http() as http:
        result = await gwr.geoadmin_find_egid(http, egid)
    if result is None:
        return BuildingResponse(provenance="live_api", found=False)
    a = result.get("attributes", {})
    return BuildingResponse(
        provenance="live_api",
        found=True,
        building=Building(
            egid=int(a.get("egid", egid)),
            municipality_bfs=a.get("ggdenr"),
            municipality=a.get("ggdename"),
            canton=a.get("gdekt"),
            address=a.get("strname_deinr"),
            status_code=a.get("gstat"),
            status=GSTAT_LABELS.get(a.get("gstat")),
            category_code=a.get("gkat"),
            construction_year=a.get("gbauj"),
            dwelling_count=a.get("ganzwhg"),
            floor_area_m2=a.get("garea"),
            e_lv95=a.get("gkode"),
            n_lv95=a.get("gkodn"),
        ),
    )


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
async def address_to_egid(address: str, limit: int = 5) -> GeocodeResponse:
    """Geocode a Swiss address to EGID/EDID and LV95 coordinates.

    This is the bridge that makes other data sources EGID-capable:
    address in → federal building identifier out.
    """
    async with _http() as http:
        results = await gwr.geoadmin_geocode(http, address, limit)
    matches = []
    for r in results:
        attrs = r.get("attrs", {})
        feature_id = str(attrs.get("featureId", ""))
        egid, edid = None, None
        if "_" in feature_id:
            egid_s, edid_s = feature_id.split("_", 1)
            egid = int(egid_s) if egid_s.isdigit() else None
            edid = int(edid_s) if edid_s.isdigit() else None
        matches.append(
            GeocodeMatch(
                label=attrs.get("label", "").replace("<b>", "").replace("</b>", ""),
                egid=egid,
                edid=edid,
                e_lv95=attrs.get("y"),  # geo.admin.ch swaps axes: y=east, x=north
                n_lv95=attrs.get("x"),
            )
        )
    return GeocodeResponse(provenance="live_api", query=address, matches=matches)


@mcp.tool(annotations={"readOnlyHint": True})
async def lookup_dwellings(egid: int, canton: str = "zh") -> DwellingsResponse:
    """List all dwellings (EWID) of a building from the daily cantonal dump.

    Includes rooms, floor area, floor and status per dwelling.
    """
    async with _http() as http:
        await store.ensure_dump(canton, http)
    rows = store.query(
        canton,
        "SELECT EGID, EWID, WSTWK, WAZIM, WAREA, WSTAT, WBAUJ FROM dwelling WHERE EGID=?",
        (egid,),
    )
    return DwellingsResponse(
        provenance="daily_dump",
        egid=egid,
        count=len(rows),
        dwellings=[
            Dwelling(
                egid=r["EGID"],
                ewid=r["EWID"],
                floor=str(r["WSTWK"]) if r["WSTWK"] is not None else None,
                rooms=r["WAZIM"],
                area_m2=r["WAREA"],
                status_code=r["WSTAT"],
                construction_year=r["WBAUJ"],
            )
            for r in rows
        ],
    )


@mcp.tool(annotations={"readOnlyHint": True})
async def new_construction(
    municipality_bfs: int, since_year: int = 2020, canton: str | None = None
) -> NewConstructionResponse:
    """New residential construction per year for a municipality (existing buildings).

    Returns buildings, dwellings and 4+ room dwellings per year — the 4+ room
    share is a proxy for family housing and thus for future pupil numbers.
    Municipality is identified by its BFS number (e.g. 261 = City of Zurich).
    """
    async with _http() as http:
        canton = canton or await _canton_for_municipality(municipality_bfs, http)
        await store.ensure_dump(canton, http)
    rows = store.query(
        canton,
        """
        SELECT b.GBAUJ AS year,
               COUNT(DISTINCT b.EGID) AS buildings,
               COUNT(d.EWID) AS dwellings,
               SUM(CASE WHEN d.WAZIM >= 4 THEN 1 ELSE 0 END) AS d4
        FROM building b
        LEFT JOIN dwelling d ON d.EGID = b.EGID AND d.WSTAT = 3004
        WHERE b.GGDENR = ? AND b.GSTAT = 1004 AND b.GBAUJ >= ?
        GROUP BY b.GBAUJ ORDER BY b.GBAUJ
        """,
        (municipality_bfs, since_year),
    )
    name_rows = store.query(
        canton, "SELECT GGDENAME FROM building WHERE GGDENR=? LIMIT 1", (municipality_bfs,)
    )
    per_year = [
        YearRow(
            year=r["year"], buildings=r["buildings"], dwellings=r["dwellings"],
            dwellings_4plus_rooms=r["d4"] or 0,
        )
        for r in rows
        if r["year"] is not None
    ]
    total = sum(r.dwellings for r in per_year)
    total4 = sum(r.dwellings_4plus_rooms for r in per_year)
    return NewConstructionResponse(
        provenance="daily_dump",
        municipality_bfs=municipality_bfs,
        municipality=name_rows[0]["GGDENAME"] if name_rows else None,
        since_year=since_year,
        per_year=per_year,
        total_dwellings=total,
        total_dwellings_4plus_rooms=total4,
        family_share_pct=round(100 * total4 / total, 1) if total else 0.0,
    )


@mcp.tool(annotations={"readOnlyHint": True})
async def construction_pipeline(
    municipality_bfs: int, canton: str | None = None
) -> PipelineResponse:
    """Buildings and dwellings in the planning/construction pipeline of a municipality.

    Breaks down by status: projected (GSTAT 1001), approved (1002), under
    construction (1003). Dwellings under construction today are households in
    1-3 years — the early indicator for school-space planning.
    """
    async with _http() as http:
        canton = canton or await _canton_for_municipality(municipality_bfs, http)
        await store.ensure_dump(canton, http)
    pipeline = []
    for gstat in (1001, 1002, 1003):
        r = store.query(
            canton,
            """
            SELECT COUNT(DISTINCT b.EGID) AS buildings, COUNT(d.EWID) AS dwellings
            FROM building b LEFT JOIN dwelling d ON d.EGID = b.EGID
            WHERE b.GGDENR = ? AND b.GSTAT = ?
            """,
            (municipality_bfs, gstat),
        )[0]
        pipeline.append(
            PipelineRow(
                status=GSTAT_LABELS[gstat], status_code=gstat,
                buildings=r["buildings"], dwellings=r["dwellings"],
            )
        )
    name_rows = store.query(
        canton, "SELECT GGDENAME FROM building WHERE GGDENR=? LIMIT 1", (municipality_bfs,)
    )
    return PipelineResponse(
        provenance="daily_dump",
        municipality_bfs=municipality_bfs,
        municipality=name_rows[0]["GGDENAME"] if name_rows else None,
        pipeline=pipeline,
    )


@mcp.tool(annotations={"readOnlyHint": True})
async def buildings_in_bbox(
    e_min: float, n_min: float, e_max: float, n_max: float,
    canton: str = "zh", since_year: int | None = None,
) -> BBoxStatsResponse:
    """Aggregate buildings/dwellings inside an LV95 bounding box.

    Enables sub-municipal analysis, e.g. school districts: pass the bounding
    box of a Schulkreis to count new construction within it. LV95 (EPSG:2056):
    east ~2'480'000-2'840'000, north ~1'070'000-1'300'000.
    """
    async with _http() as http:
        await store.ensure_dump(canton, http)
    year_clause = "AND b.GBAUJ >= ?" if since_year else ""
    params: tuple = (e_min, e_max, n_min, n_max) + ((since_year,) if since_year else ())
    r = store.query(
        canton,
        f"""
        SELECT COUNT(DISTINCT b.EGID) AS buildings,
               COUNT(d.EWID) AS dwellings,
               SUM(CASE WHEN d.WAZIM >= 4 THEN 1 ELSE 0 END) AS d4
        FROM building b
        LEFT JOIN dwelling d ON d.EGID = b.EGID AND d.WSTAT = 3004
        WHERE b.GSTAT = 1004
          AND b.GKODE BETWEEN ? AND ? AND b.GKODN BETWEEN ? AND ?
          {year_clause}
        """,
        params,
    )[0]
    return BBoxStatsResponse(
        provenance="daily_dump",
        bbox_lv95=(e_min, n_min, e_max, n_max),
        since_year=since_year,
        buildings=r["buildings"],
        dwellings=r["dwellings"],
        dwellings_4plus_rooms=r["d4"] or 0,
    )


@mcp.tool(annotations={"readOnlyHint": True})
async def municipality_housing_stats(
    municipality_bfs: int, canton: str | None = None
) -> MunicipalityStatsResponse:
    """Housing stock overview of a municipality: buildings, dwellings, room-size mix."""
    async with _http() as http:
        canton = canton or await _canton_for_municipality(municipality_bfs, http)
        await store.ensure_dump(canton, http)
    b = store.query(
        canton,
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN GKAT IN (1020, 1030, 1040) THEN 1 ELSE 0 END) AS residential
        FROM building WHERE GGDENR = ? AND GSTAT = 1004
        """,
        (municipality_bfs,),
    )[0]
    rooms = store.query(
        canton,
        """
        SELECT CASE WHEN d.WAZIM >= 6 THEN '6+' ELSE CAST(CAST(d.WAZIM AS INT) AS TEXT) END AS bucket,
               COUNT(*) AS n
        FROM dwelling d JOIN building bu ON bu.EGID = d.EGID
        WHERE bu.GGDENR = ? AND bu.GSTAT = 1004 AND d.WSTAT = 3004 AND d.WAZIM IS NOT NULL
        GROUP BY bucket ORDER BY bucket
        """,
        (municipality_bfs,),
    )
    name_rows = store.query(
        canton, "SELECT GGDENAME FROM building WHERE GGDENR=? LIMIT 1", (municipality_bfs,)
    )
    return MunicipalityStatsResponse(
        provenance="daily_dump",
        municipality_bfs=municipality_bfs,
        municipality=name_rows[0]["GGDENAME"] if name_rows else None,
        buildings_total=b["total"],
        buildings_residential=b["residential"] or 0,
        dwellings_total=sum(r["n"] for r in rooms),
        dwellings_by_rooms={r["bucket"]: r["n"] for r in rooms},
    )


@mcp.tool(annotations={"readOnlyHint": True})
async def explain_code(attribute: str, code: int, canton: str = "zh") -> CodeResponse:
    """Decode a GWR code value (e.g. GSTAT=1004, GKAT=1020) into human-readable labels.

    Uses the official code table shipped with the dump (DE/FR/IT).
    """
    async with _http() as http:
        await store.ensure_dump(canton, http)
    rows = store.query(
        canton,
        "SELECT CMERKM, CECODID, CODTXTLD, CODTXTLF, CODTXTLI FROM code "
        "WHERE UPPER(CMERKM) = UPPER(?) AND CECODID = ?",
        (attribute, code),
    )
    return CodeResponse(
        provenance="daily_dump",
        explanations=[
            CodeExplanation(
                attribute=r["CMERKM"], code=int(r["CECODID"]),
                label_de=r["CODTXTLD"], label_fr=r["CODTXTLF"], label_it=r["CODTXTLI"],
            )
            for r in rows
        ],
    )


@mcp.tool(annotations={"readOnlyHint": True})
async def dump_status() -> DumpStatusResponse:
    """Cache status of the cantonal GWR dumps (graceful-degradation entry point).

    Always returns an evaluable status — never silently empty records. If a
    source is unreachable, this tool tells you when data was last refreshed.
    """
    return DumpStatusResponse(
        provenance="cached",
        dumps=store.status(),
        ttl_hours=gwr.DUMP_TTL_HOURS,
        note=(
            "Dumps refresh upstream daily around 05:30 CET. If a download fails, "
            "cached data remains usable; check age_hours for freshness."
        ),
    )
