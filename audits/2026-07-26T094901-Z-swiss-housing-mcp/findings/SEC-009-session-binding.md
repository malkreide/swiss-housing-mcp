## Finding: SEC-009 — Session-ID Cryptographic Binding

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `SEC-009` |
| **PDF-Reference** | Sec 6.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

auth_model is none and there is no custom session code; session-id handling for the HTTP transport is delegated to the FastMCP SDK default. No explicit user<->session binding, TTL, or invalidation is asserted in code.

### Expected Behavior

Session IDs generated with >=128-bit entropy, cryptographically bound to a validated user identity, with explicit TTL and server-side invalidation.

### Evidence

- profile.yaml — auth_model: none; `src/swiss_housing_mcp/server.py:36` — FastMCP with no session customisation
- no OAuth/user identity in the codebase (public, anonymous, read-only)

### Risk Description

Low for an anonymous read-only public-data server (no per-user data to protect), but if auth is ever added the HTTP transport has no session-binding scaffold and would need it from scratch.

### Remediation

Keep HTTP transport as a documented opt-in for trusted networks now; if multi-tenant auth is added, implement signed session tokens binding user_id:session_id with TTL and logout invalidation.

### Effort Estimate

**L**

### Dependencies / Blockers

Blocked-until: an auth model is introduced

### Verification After Fix

- Re-run the `SEC-009` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
