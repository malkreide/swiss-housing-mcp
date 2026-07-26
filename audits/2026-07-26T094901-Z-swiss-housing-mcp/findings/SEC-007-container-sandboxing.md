## Finding: SEC-007 — Container-Sandboxing: minimale Privilegien

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `SEC-007` |
| **PDF-Reference** | Sec 6.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

There is no Dockerfile in the repo. SECURITY.md records container sandboxing as an accepted risk for the local-stdio public-data profile.

### Expected Behavior

For any container/cloud deployment: non-root USER (uid>=10000), read-only root FS, dropped capabilities, seccomp RuntimeDefault.

### Evidence

- no Dockerfile present (find . -name Dockerfile — none)
- `SECURITY.md:45-51` — container sandboxing documented as accepted risk

### Risk Description

No hardened image exists, so a future Render/Railway deployment could run as root with a writable FS; accepted while the server stays local-stdio.

### Remediation

Ship a hardened Dockerfile (non-root, read-only FS, dropped caps) before any cloud deployment; keep the accepted-risk note until then.

### Effort Estimate

**M**

### Dependencies / Blockers

Blocked-until: cloud deployment decision

### Verification After Fix

- Re-run the `SEC-007` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
