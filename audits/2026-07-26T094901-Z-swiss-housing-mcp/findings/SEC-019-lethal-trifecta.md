## Finding: SEC-019 — Lethal Trifecta vermeiden: Server-Separation

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `SEC-019` |
| **PDF-Reference** | Sec 6.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

The server is fully read-only, egress is confined to fixed BFS/geo.admin.ch hosts with no arbitrary send/exfiltration path, and the data is public — so it holds at most 2 of the 3 trifecta capabilities. This structural safety is real but is not documented as an assessed decision (no trifecta ADR).

### Expected Behavior

A documented trifecta assessment confirming <=2 of the 3 capabilities, with recipient allow-lists as frozensets if any send capability exists.

### Evidence

- `src/swiss_housing_mcp/server.py` — all 9 tools read-only; `gwr.py:30-31` egress to fixed hosts only
- `SECURITY.md:32` — documents the no-write / read-only posture (but not framed as a trifecta assessment)

### Risk Description

Structurally safe today, but without a written assessment a future contributor could add a send-capable tool (webhook/mail) without realising it completes the trifecta.

### Remediation

Add a short 'Lethal Trifecta' assessment to SECURITY.md/docs recording the <=2-capability status and the rule that any send capability requires a frozenset allow-list + sign-off.

### Effort Estimate

**S**

### Dependencies / Blockers

None

### Verification After Fix

- Re-run the `SEC-019` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
