## Finding: OPS-002 — Doku-Standard: Security-Sektion + Architektur-Diagramm

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `OPS-002` |
| **PDF-Reference** | Sec 4.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

README carries most required sections (anchor, install, features, config, limits, license) and README.de.md mirrors them, with a bilingual CONTRIBUTING and a Keep-a-Changelog CHANGELOG. Missing: a dedicated Security section in the README and an ASCII/Mermaid architecture data-flow diagram — the 'Project Structure' block is a file tree, not an architecture diagram.

### Expected Behavior

All 8 mandatory README sections including Security and an architecture diagram (ASCII or Mermaid).

### Evidence

- `README.md:120` — 'Project Structure' is a file tree, not a data-flow diagram
- `README.md` — grep security/mermaid/diagram returns nothing (security lives only in SECURITY.md)

### Risk Description

A reader can't see the dump-first/API-fallback data flow at a glance, and the README doesn't point to the security posture; slows onboarding and audit.

### Remediation

Add a Mermaid/ASCII diagram of client -> tools -> (SQLite dump | geo.admin.ch) and a short README Security section linking SECURITY.md.

### Effort Estimate

**S**

### Dependencies / Blockers

None

### Verification After Fix

- Re-run the `OPS-002` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
