## Finding: SEC-005 — DNS-Rebinding-Prevention: DNS-Pinning gegen TOCTOU

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `SEC-005` |
| **PDF-Reference** | Sec 6.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

Each request is a single httpx GET against fixed public hosts with no user-controlled hostname, so rebinding risk is low. There is no DNS-pinning / single-resolution guard.

### Expected Behavior

Resolve DNS once and pin the resolved IP for the connection while keeping the original hostname for SNI/Host and cert validation.

### Evidence

- `src/swiss_housing_mcp/gwr.py:70-86` — fetch_with_retry issues plain httpx.get against fixed hosts

### Risk Description

A rebinding attacker controlling DNS for the upstream host could in theory swap the IP between resolution and connect; residual risk is low because hosts are fixed federal endpoints.

### Remediation

If/when SEC-004 is implemented, pin the resolved IP via a custom transport/resolver; otherwise accept-risk with a documented note given fixed public hosts.

### Effort Estimate

**M**

### Dependencies / Blockers

Depends on SEC-004

### Verification After Fix

- Re-run the `SEC-005` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
