## Finding: OPS-001 — Test-Strategie: Unit-Tests mocked + Live-Tests gemarkert

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `OPS-001` |
| **PDF-Reference** | Sec 4.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

The test architecture is exemplary: respx-mocked units, a registered `live` marker, CI running `pytest -m 'not live'`, and a separate nightly live job. Coverage, however, is thin: 7 unit + 2 live tests for 9 tools, and they exercise the gwr client layer only — the 9 @mcp.tool handlers are not directly tested.

### Expected Behavior

>=5 unit tests and >=1 live test per tool, covering the tool handlers (not just the client helpers).

### Evidence

- `tests/test_server.py:38-46` — respx-mocked unit test (client layer)
- `pyproject.toml:52-54` — live marker registered; `.github/workflows/ci.yml:42-46` runs pytest -m 'not live'; ci.yml:64-82 nightly live job
- `tests/test_server.py` — 7 not-live + 2 live tests total for 9 tools

### Risk Description

The SQL-heavy aggregation tools (new_construction, construction_pipeline, buildings_in_bbox, municipality_housing_stats) have no tests; a regression in a JOIN or GROUP BY would ship undetected.

### Remediation

Add handler-level tests with a seeded in-memory/temp SQLite dump for each aggregation tool; add one live test per tool.

### Effort Estimate

**M**

### Dependencies / Blockers

None

### Verification After Fix

- Re-run the `OPS-001` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
