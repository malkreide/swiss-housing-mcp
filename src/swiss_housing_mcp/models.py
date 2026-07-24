"""Pydantic v2 response models. Every response carries source + provenance."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ATTRIBUTION = (
    "Data: Federal Register of Buildings and Dwellings (GWR/RegBL), "
    "Swiss Federal Statistical Office (BFS) — OGD, free use with attribution. "
    "Daily public extract via public.madd.bfs.admin.ch and api3.geo.admin.ch."
)

Provenance = Literal["daily_dump", "live_api", "cached"]


class Envelope(BaseModel):
    source: str = Field(default=ATTRIBUTION)
    provenance: Provenance


class Building(BaseModel):
    egid: int
    municipality_bfs: int | None = Field(default=None, description="GGDENR — BFS municipality number")
    municipality: str | None = None
    canton: str | None = None
    address: str | None = None
    status_code: int | None = Field(default=None, description="GSTAT (1001 planned … 1004 existing … 1007 demolished)")
    status: str | None = None
    category_code: int | None = Field(default=None, description="GKAT")
    category: str | None = None
    construction_year: int | None = Field(default=None, description="GBAUJ")
    dwelling_count: int | None = Field(default=None, description="GANZWHG")
    floor_area_m2: int | None = Field(default=None, description="GAREA")
    e_lv95: float | None = Field(default=None, description="GKODE (LV95 east)")
    n_lv95: float | None = Field(default=None, description="GKODN (LV95 north)")


class BuildingResponse(Envelope):
    found: bool
    building: Building | None = None


class Dwelling(BaseModel):
    egid: int
    ewid: int
    floor: str | None = Field(default=None, description="WSTWK, decoded")
    rooms: float | None = Field(default=None, description="WAZIM")
    area_m2: int | None = Field(default=None, description="WAREA")
    status_code: int | None = Field(default=None, description="WSTAT")
    construction_year: int | None = Field(default=None, description="WBAUJ")


class DwellingsResponse(Envelope):
    egid: int
    count: int
    dwellings: list[Dwelling]


class GeocodeMatch(BaseModel):
    label: str
    egid: int | None
    edid: int | None
    e_lv95: float | None
    n_lv95: float | None


class GeocodeResponse(Envelope):
    query: str
    matches: list[GeocodeMatch]


class YearRow(BaseModel):
    year: int
    buildings: int
    dwellings: int
    dwellings_4plus_rooms: int


class NewConstructionResponse(Envelope):
    municipality_bfs: int
    municipality: str | None
    since_year: int
    per_year: list[YearRow]
    total_dwellings: int
    total_dwellings_4plus_rooms: int
    family_share_pct: float = Field(description="Share of 4+ room dwellings — proxy for family housing")


class PipelineRow(BaseModel):
    status: str
    status_code: int
    buildings: int
    dwellings: int


class PipelineResponse(Envelope):
    municipality_bfs: int
    municipality: str | None
    pipeline: list[PipelineRow]
    note: str = Field(
        default=(
            "Dwellings under construction today are households in 1-3 years — "
            "an early indicator for school-space planning."
        )
    )


class BBoxStatsResponse(Envelope):
    bbox_lv95: tuple[float, float, float, float] = Field(description="(e_min, n_min, e_max, n_max)")
    since_year: int | None
    buildings: int
    dwellings: int
    dwellings_4plus_rooms: int


class MunicipalityStatsResponse(Envelope):
    municipality_bfs: int
    municipality: str | None
    buildings_total: int
    buildings_residential: int
    dwellings_total: int
    dwellings_by_rooms: dict[str, int]


class DumpStatusResponse(Envelope):
    dumps: list[dict]
    ttl_hours: float
    note: str


class CodeExplanation(BaseModel):
    attribute: str
    code: int
    label_de: str | None
    label_fr: str | None
    label_it: str | None


class CodeResponse(Envelope):
    explanations: list[CodeExplanation]
