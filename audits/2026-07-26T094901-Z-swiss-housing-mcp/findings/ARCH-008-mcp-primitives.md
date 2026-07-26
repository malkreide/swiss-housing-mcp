## Finding: ARCH-008 — Drei Primitive nutzen: Tools, Resources und Prompts

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `ARCH-008` |
| **PDF-Reference** | Anhang A2 |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

The server exposes only Tools; there are no Resources or Prompts, and the README contains no documented justification for the tools-only choice.

### Expected Behavior

Use at least two of the three primitives, OR document in the README why only Tools are used. Idempotent read-only lookups are Resource candidates.

### Evidence

- grep `@mcp.resource`/`@mcp.prompt` in src/ — no matches
- `README.md` / `README.de.md` — grep primitive/resource/prompt returns nothing

### Risk Description

All read-only lookups sit in the tool manifest, inflating token cost per call and forgoing Resource cache/URI benefits; acceptable for a Phase-1 wrapper but undocumented.

### Remediation

Either add a short 'MCP Primitives' README section justifying tools-only for Phase 1, or migrate side-effect-free lookups (dump_status, explain_code) to Resources with a documented URI scheme.

### Effort Estimate

**M**

### Dependencies / Blockers

None

### Verification After Fix

- Re-run the `ARCH-008` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
