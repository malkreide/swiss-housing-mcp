## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `ARCH-003` |
| **PDF-Reference** | Sec 2.2 |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

Not-found is handled with structured envelopes (BuildingResponse(found=False), dump_status note) rather than bare []/None, which avoids the worst anti-pattern. However there is no fuzzy-match / suggestion fallback and no `match_type` field.

### Expected Behavior

Non-sensitive search tools should, on an empty exact result, return fuzzy/related results or actionable suggestions plus a `match_type` (exact|fuzzy|none) field.

### Evidence

- `src/swiss_housing_mcp/server.py:84-85` — returns BuildingResponse(provenance='live_api', found=False) with no hint
- `src/swiss_housing_mcp/server.py:135` — address_to_egid returns matches list with no fuzzy/suggestion path

### Risk Description

On a typo'd address or unknown EGID the LLM gets found=False with no next step, risking a dead-end or a hallucinated answer instead of a refined retry.

### Remediation

Add a `match_type` field to responses; on empty geocode/lookup results surface near-matches or a hint (e.g. suggest address_to_egid before lookup_building). Public data, so heuristics leak nothing.

### Effort Estimate

**S**

### Dependencies / Blockers

None

### Verification After Fix

- Re-run the `ARCH-003` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
