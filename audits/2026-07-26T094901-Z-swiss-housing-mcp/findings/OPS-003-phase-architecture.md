## Finding: OPS-003 — Phasenarchitektur: Read-only First explizit deklariert

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `OPS-003` |
| **PDF-Reference** | Sec 4.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

Phase-1 is referenced only in prose ('Phase 1 is authentication-free'), and all tools are readOnlyHint:True which is consistent with a read-only Phase 1. There is no explicit phase-declaration section, no roadmap file, and no documented phase-transition prerequisites.

### Expected Behavior

An explicit Phase 1/2/3 declaration, a roadmap file, and documented prerequisites (audit/ISDS/DSG gates) for phase transitions.

### Evidence

- `README.md:73` — 'Phase 1 is authentication-free' (prose only)
- `README.md:38` — references Phase-1 tools; no ROADMAP file present

### Risk Description

Without an explicit phase contract, a future write-capable tool could be added without triggering the required security/DSG review gate.

### Remediation

Add a 'Project Phase' README section declaring Phase 1 (read-only) and the gate conditions for Phase 2; add a ROADMAP.md.

### Effort Estimate

**S**

### Dependencies / Blockers

None

### Verification After Fix

- Re-run the `OPS-003` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
