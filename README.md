# swiss-housing-mcp

> Part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide/swiss-public-data-mcp) — open-source MCP servers connecting AI agents to Swiss public data. **Private project, independent of any employer or institutional affiliation.**

[![Version](https://img.shields.io/badge/version-0.1.0-blue)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](pyproject.toml)
[![MCP](https://img.shields.io/badge/MCP-server-8A2BE2)](https://modelcontextprotocol.io/)

> MCP server for the Swiss Federal Register of Buildings and Dwellings (GWR/RegBL) — buildings, dwellings, and the construction pipeline

[🇩🇪 Deutsche Version](README.de.md)

---

## 🎯 Anchor Demo Query

> *«How many dwellings were newly built in the City of Zurich since 2020, how many with 4+ rooms — and how many are currently under construction?»*

Verified against the live dump on 2026-07-24: **16'164 new dwellings** since 2020 (27.4% with 4+ rooms — the family-housing proxy), and **7'287 dwellings currently under construction**. Dwellings under construction today are households in 1–3 years: the early indicator for school-space planning.

### Demo

![Demo: Claude using new_construction and construction_pipeline](docs/assets/demo.svg)

---

## Overview

The GWR/RegBL is to buildings what Zefix is to companies: not one data source among many, but the **federal register** whose identifiers (EGID for buildings, EWID for dwellings) serve as join keys across Swiss administrative data. This server exposes the register's public extract through MCP tools — building lookups, address geocoding, per-municipality construction statistics, sub-municipal bounding-box analysis, and the planning/construction pipeline.

`address_to_egid` is the plug that makes other data sources EGID-capable: address in, federal identifier and LV95 coordinates out.

## Architecture decision

This server uses **Architecture B (Hybrid: Dump-first, API-fallback)**.

Rationale (verified live on 2026-07-24):

- The public cantonal dump (`public.madd.bfs.admin.ch/{canton}.zip`) is refreshed **daily** (~05:30 CET) and ships a ready-made `data.sqlite` with tables `building` (399'830 rows for ZH), `entrance`, `dwelling` (894'631 rows for ZH), and `code`. No CSV parsing, no auth.
- `api3.geo.admin.ch` (find / identify / SearchServer) works reliably without authentication for single-entity lookups and geocoding, but does not scale to area-wide aggregations (result limits).
- A MADD REST endpoint probed at `/api/buildings/{egid}` returned 404; it is excluded until path and auth status are clarified — no blocker, since all Phase-1 tools work without it.

Consequences:

- Cantonal dumps are cached on disk with a 24 h TTL (configurable via `SWISS_HOUSING_DUMP_TTL_HOURS`).
- Aggregations and spatial queries run as read-only SQL against the cached SQLite; single lookups and geocoding hit the live API.
- Every response carries `source` (attribution) and `provenance` (`daily_dump` | `live_api` | `cached`).

### Live probe findings (2026-07-24)

| Endpoint | HTTP | Status | Note |
|---|---|---|---|
| `api3.geo.admin.ch …/find` (EGID lookup) | 200 | ✅ works | full attribute set, no auth |
| `api3.geo.admin.ch …/identify` (coordinates) | 200 | ✅ works | 77 attributes incl. EGID/EWID |
| `…/SearchServer` (address → EGID) | 200 | ✅ works | `featureId` = `{EGID}_{EDID}`; axis swap: `y`=east, `x`=north |
| `public.madd.bfs.admin.ch/zh.zip` | 200 | ✅ works | 121 MB, daily refresh, contains `data.sqlite` |
| `madd.bfs.admin.ch/api/buildings/{egid}` | 404 | ❌ excluded | path/auth unclear |
| Invalid EGID on find | 200 | ⚠️ soft error | empty `results` array — not an HTTP error |

## Features

- **`lookup_building(egid)`** — single building by federal identifier (live API)
- **`address_to_egid(address)`** — geocode any Swiss address to EGID/EDID + LV95
- **`lookup_dwellings(egid)`** — all dwellings of a building with rooms, area, floor
- **`new_construction(municipality_bfs, since_year)`** — yearly new construction incl. 4+ room family-housing share
- **`construction_pipeline(municipality_bfs)`** — projected / approved / under construction
- **`buildings_in_bbox(e_min, n_min, e_max, n_max)`** — sub-municipal analysis (e.g. school districts)
- **`municipality_housing_stats(municipality_bfs)`** — housing stock and room-size mix
- **`explain_code(attribute, code)`** — decode GWR codes via the official DE/FR/IT code table
- **`dump_status()`** — cache freshness, graceful-degradation entry point

## Prerequisites

- Python 3.10+
- ~130 MB disk per cached cantonal dump (ZH)
- No API keys — Phase 1 is authentication-free

## Installation

```bash
uvx swiss-housing-mcp        # once published on PyPI

# or from source
pip install -e .
```

## Usage / Quickstart

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "swiss-housing": {
      "command": "uvx",
      "args": ["swiss-housing-mcp"]
    }
  }
}
```

**Cloud (Render/Railway):**

```bash
SWISS_HOUSING_TRANSPORT=streamable-http PORT=8000 swiss-housing-mcp
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `SWISS_HOUSING_TRANSPORT` | `stdio` | `stdio` \| `streamable-http` \| `sse` |
| `SWISS_HOUSING_CACHE` | `~/.cache/swiss-housing-mcp` | Dump cache directory |
| `SWISS_HOUSING_DUMP_TTL_HOURS` | `24` | Dump freshness window |

## MCP Protocol Version

This server speaks **two protocol eras** over the same endpoint. The client's
first request on a connection decides which one applies; a later claim from the
other era is refused.

| Era | Revision | Who reaches it |
|---|---|---|
| `initialize` handshake | `2024-11-05` … **`2025-11-25`** | What today's clients speak. The server answers with the revision asked for, or with the `2025-11-25` ceiling when the request asks for something newer. |
| Per-request envelope | **`2026-07-28`** | A request carrying the `2026-07-28` `_meta` envelope opens a modern connection. |

Both revisions are pinned in
[`tests/test_protocol_version.py`](tests/test_protocol_version.py) and asserted
against the installed SDK, so a Dependabot bump of `mcp` cannot move either one
silently. This server builds no ASGI app to send an `initialize` through, so
the gate asserts the SDK constants rather than a measured response — the
weaker form, named rather than left unsaid.

Note that the SDK's `LATEST_PROTOCOL_VERSION` is an alias for the **modern**
era, not for the handshake era — pinning against it alone would leave the era
that current clients actually negotiate free to drift.

**Update policy.** When the gate fails, do not edit the constant blindly: read
the spec changelog between the two revisions, verify the server still behaves,
then move the constant, this section, `README.de.md` and
[`CHANGELOG.md`](CHANGELOG.md) together.

## Testing

```bash
PYTHONPATH=src pytest tests/ -m "not live"   # CI-safe
PYTHONPATH=src pytest tests/ -m live         # against real upstream
```

## Project Structure

```
swiss-housing-mcp/
├── src/swiss_housing_mcp/
│   ├── server.py      # FastMCP tools (9)
│   ├── gwr.py         # Dump store + geo.admin.ch client + retry
│   ├── models.py      # Pydantic v2 envelopes (source + provenance)
│   └── __main__.py    # Dual-transport entry point
├── tests/             # respx-mocked + @pytest.mark.live
└── .github/workflows/ # CI + OIDC PyPI publish
```

## Known Limitations

- The public extract omits person-related and some sensitive attributes of the full GWR; official data deliveries to authorities go through the BFS/MADD channel.
- Coordinates are building reference points (LV95), not footprint polygons — polygon joins (e.g. exact school-district boundaries) need external geometries; `buildings_in_bbox` covers the rectangular approximation.
- `GBAUJ` (construction year) is missing for a share of older buildings; period codes (`GBAUP`) exist as fallback but are not yet exposed.
- Municipality→canton resolution is seeded for common cases; pass `canton` explicitly for others.
- Housing-market indices (IMPI, construction price index, vacancy rate) deliberately live in `swiss-statistics-mcp` — this server is the register layer, not the statistics layer.

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) ([Deutsch](CONTRIBUTING.de.md)).

## Security

Read-only, no PII, no authentication — a public federal register accessed through
a fixed set of endpoints. See [SECURITY.md](SECURITY.md) ([Deutsch](SECURITY.de.md))
for the full posture and how to report a vulnerability.

## License

MIT License — see [LICENSE](LICENSE). Data: GWR/RegBL, Swiss Federal Statistical Office (BFS), open government data with attribution.

## Author

**Hayal Oezkan** · [github.com/malkreide](https://github.com/malkreide)

## Credits & Related Projects

- Data: [Federal Statistical Office — GWR/RegBL](https://www.housing-stat.ch/), [geo.admin.ch](https://api3.geo.admin.ch/)
- Portfolio siblings: [`swiss-statistics-mcp`](https://github.com/malkreide/swiss-statistics-mcp) (indices, STAT-TAB), [`zurich-opendata-mcp`](https://github.com/malkreide/zurich-opendata-mcp) (city-level data)


<!-- mcp-name: io.github.malkreide/swiss-housing-mcp -->
