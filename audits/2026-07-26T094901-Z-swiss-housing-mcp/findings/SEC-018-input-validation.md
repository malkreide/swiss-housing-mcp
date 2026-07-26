## Finding: SEC-018 — Input-Validation an Tool-Boundaries

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `SEC-018` |
| **PDF-Reference** | Sec 6.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

Response models use Pydantic v2 and tool inputs are type-hinted (so FastMCP applies type-level validation), and canton is whitelist-checked. But tool-input fields carry no value constraints: no ge/le on numerics, no min/max_length on the address string, and no strict/extra=forbid. The README's claim of range-checked EGID/coordinates is not enforced in code.

### Expected Behavior

All tool arguments validated with ge/le on numerics, min/max_length (+ pattern) on strings, strict=True and extra='forbid'.

### Evidence

- `src/swiss_housing_mcp/server.py:76` — egid:int with no bounds; server.py:109 limit:int with no ge/le; server.py:268-274 LV95 floats unbounded
- `src/swiss_housing_mcp/gwr.py:130-131` — canton whitelist-checked (the one enforced constraint)
- `SECURITY.md:30` — claims EGID/EWID and LV95 are range-checked (not matched by code)

### Risk Description

Unbounded inputs allow, e.g., a huge `limit` or absurd bbox to hit upstream/SQLite unnecessarily; the doc/code mismatch also misleads auditors about the actual control.

### Remediation

Introduce Pydantic Field constraints (ge/le for EGID/BFS/year/limit/LV95 ranges, max_length for address) on tool args, or Annotated types; set strict where feasible. Align SECURITY.md with the real state.

### Effort Estimate

**S**

### Dependencies / Blockers

Relates to OBS-001 (validation errors as isError)

### Verification After Fix

- Re-run the `SEC-018` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
