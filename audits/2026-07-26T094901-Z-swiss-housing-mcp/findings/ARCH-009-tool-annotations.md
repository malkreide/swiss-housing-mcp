## Finding: ARCH-009 — Tool Annotations: openWorldHint / idempotentHint vollständig

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `ARCH-009` |
| **PDF-Reference** | Anhang A5 |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

All 9 tools carry explicit annotations and readOnlyHint:True is correct (the server is fully read-only). But openWorldHint is set only on the two live-API tools; the 7 dump-fetching tools omit it despite downloading from upstream. idempotentHint is never set, and there is no annotations table in the docs.

### Expected Behavior

openWorldHint:true on every tool that reaches an external system; idempotentHint set where applicable; an annotations overview in README/docs.

### Evidence

- `src/swiss_housing_mcp/server.py:75,108` — openWorldHint:True (correct, live API)
- `src/swiss_housing_mcp/server.py:138,170,224,267,310,352` — readOnlyHint only, yet these call store.ensure_dump -> gwr.py:142 download from public.madd.bfs.admin.ch

### Risk Description

A host relying on openWorldHint for network-egress warnings would under-warn for the 7 dump tools that do reach the network; inconsistent hints erode the host's ability to reason about egress.

### Remediation

Set openWorldHint:True on all tools whose path calls ensure_dump; add idempotentHint:True (read-only queries are idempotent); publish an annotations table in the README.

### Effort Estimate

**S**

### Dependencies / Blockers

None

### Verification After Fix

- Re-run the `ARCH-009` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
