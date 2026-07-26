## Finding: SCALE-002 — Stateful Load Balancing für Streamable HTTP / SSE

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `SCALE-002` |
| **PDF-Reference** | Sec 5.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

The streamable-http/sse transports exist (dual), but there is no sticky-session or shared-state (Redis/Durable-Objects) session manager and no defined session TTL. The server is not currently cloud-deployed (profile is_cloud_deployed=false).

### Expected Behavior

Sticky sessions at the LB keyed on Mcp-Session-Id, or a shared-state session manager, with an explicit session TTL, before horizontal scaling.

### Evidence

- `src/swiss_housing_mcp/__main__.py:12-20` — streamable-http/sse selectable, single-process
- profile.yaml — is_cloud_deployed: false, deployment: [local-stdio]

### Risk Description

If the HTTP transport is ever run behind more than one replica, session-bound requests would land on the wrong instance and fail; latent until a cloud move.

### Remediation

Document a single-instance constraint for the HTTP transport now; add sticky-session/Redis session state before any multi-replica deployment.

### Effort Estimate

**M**

### Dependencies / Blockers

Blocked-until: cloud deployment decision

### Verification After Fix

- Re-run the `SCALE-002` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
