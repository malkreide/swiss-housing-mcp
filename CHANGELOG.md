# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- **SEC-016 (0.0.0.0 binding / NeighborJack):** the HTTP transports defaulted
  `HOST` to `0.0.0.0`, binding all interfaces. Now default to `127.0.0.1`;
  exposing all interfaces requires an explicit `HOST=0.0.0.0`.

### Added
- Portfolio-standard repository files, aligning the repo with the sibling
  `*-mcp` servers: `.github/workflows/ci.yml` (test/lint/live) and `publish.yml`
  (OIDC PyPI + MCP Registry, tag-guarded version derivation),
  `CONTRIBUTING.md`/`.de.md`, `SECURITY.md`/`.de.md`, `EXAMPLES.md`, and
  `server.json` (MCP Registry manifest)

### Changed
- `pyproject.toml` aligned to portfolio standards: `requires-python >=3.11`,
  `mcp[cli]` upper-bounded (`<2.0.0`), `testpaths`, and a `Changelog` project URL
- `ruff format` applied to `src/` (formatting only, no behaviour change)

## [0.1.0] - 2026-07-24

### Added
- Initial release with 9 tools: `lookup_building`, `address_to_egid`,
  `lookup_dwellings`, `new_construction`, `construction_pipeline`,
  `buildings_in_bbox`, `municipality_housing_stats`, `explain_code`,
  `dump_status`
- Architecture B (Hybrid: Dump-first, API-fallback), verified live 2026-07-24
- Dual transport: stdio (Claude Desktop) + streamable-http/SSE (cloud)
- Retry with exponential backoff, provenance envelope in every response

### Known findings
- geo.admin.ch answers HTTP 200 with an empty `results` array for unknown
  EGIDs — an empty array is a soft "not found", not an upstream error.
- The public MADD dump ships a ready-made `data.sqlite` (building, entrance,
  dwelling, code) — no CSV parsing needed. Refreshed daily around 05:30 CET.
- SearchServer geocoding returns `featureId` as `{EGID}_{EDID}` — address
  geocoding and register lookup in one call. Note the axis swap: `y` = LV95
  east, `x` = LV95 north.
