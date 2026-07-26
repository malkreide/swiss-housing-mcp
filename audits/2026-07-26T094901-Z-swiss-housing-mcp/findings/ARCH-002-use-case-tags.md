## Finding: ARCH-002 — Tool-Beschreibung mit Use-Case-Tags

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `ARCH-002` |
| **PDF-Reference** | Sec 2.2 |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

All 9 tool docstrings are multi-sentence and give real prose context (e.g. server.py:177-179 explains the 4+ room share as a family-housing proxy), but none uses structured `<use_case>` / `<important_notes>` / `<example>` tags.

### Expected Behavior

At least 80% of tools carry a structured use-case tag (or equivalent) so the LLM can differentiate semantically similar tools reliably.

### Evidence

- `src/swiss_housing_mcp/server.py:76-81` — lookup_building docstring: prose only, no tags
- `src/swiss_housing_mcp/server.py:225-232` — construction_pipeline docstring: prose only

### Risk Description

With several overlapping stats tools (new_construction, construction_pipeline, municipality_housing_stats, buildings_in_bbox), an LLM may pick the wrong one; prose descriptions are weaker discriminators than explicit tags.

### Remediation

Add `<use_case>` and, where relevant, `<important_notes>` tags to each description string, keeping the existing prose. No behavioural change.

### Effort Estimate

**S**

### Dependencies / Blockers

None

### Verification After Fix

- Re-run the `ARCH-002` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
