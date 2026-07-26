## Finding: OBS-003 — Structured Logging mit RFC 5424 Severity-Stufen

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `OBS-003` |
| **PDF-Reference** | Sec 3.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

There is no logging framework at all (no structlog/loguru/logging), so no severity levels or per-call bound context. There are also no print() statements. SECURITY.md records structured logging as an accepted risk for the stdio profile.

### Expected Behavior

A structured logger (structlog/loguru) emitting JSON/logfmt with >=4 severity levels and per-tool-call bound context.

### Evidence

- grep structlog/loguru/logging/print in src/ — no logging framework and no print()
- `SECURITY.md:53-56` — 'Structured logging: accepted risk' for the stdio profile

### Risk Description

No observability: a failing dump download or upstream error leaves no trace for the operator; acceptable for local stdio but blocks any cloud/SSE move.

### Remediation

Add structlog with a stderr WriteLoggerFactory (see OBS-004); bind tool name + correlation id per call; keep it off stdout.

### Effort Estimate

**M**

### Dependencies / Blockers

Pairs with OBS-004 (stderr sink)

### Verification After Fix

- Re-run the `OBS-003` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
