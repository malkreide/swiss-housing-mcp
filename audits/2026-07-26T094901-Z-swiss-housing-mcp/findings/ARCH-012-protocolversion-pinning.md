## Finding: ARCH-012 — protocolVersion-Pinning + SDK-Update-Disziplin

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `ARCH-012` |
| **PDF-Reference** | Anhang A9 |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

CHANGELOG.md exists in Keep-a-Changelog format, but the MCP protocolVersion is not pinned in code (SDK default is used), there is no README 'MCP Protocol Version' section, and no dependabot/renovate config for SDK-update discipline.

### Expected Behavior

Explicit protocolVersion pin in the server, a README protocol-version + update-policy section, and Dependabot/Renovate for monthly SDK-update PRs.

### Evidence

- grep protocol_version/protocolVersion in src/ and server.json — no matches
- no `.github/dependabot.yml` / `renovate.json` present
- `CHANGELOG.md:1-6` — Keep-a-Changelog present (the one satisfied criterion)

### Risk Description

A future mcp SDK bump could silently change the negotiated spec version and break clients, with no changelog trail or automated update signal.

### Remediation

Pin protocol_version in FastMCP(...); add a README 'MCP Protocol Version' section with an update policy; add `.github/dependabot.yml` grouping the mcp package.

### Effort Estimate

**S**

### Dependencies / Blockers

None

### Verification After Fix

- Re-run the `ARCH-012` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
