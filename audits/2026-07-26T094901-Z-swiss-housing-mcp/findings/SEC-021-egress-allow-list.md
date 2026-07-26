## Finding: SEC-021 — Egress-Allow-List: Code-Layer und Network-Layer

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `SEC-021` |
| **PDF-Reference** | Sec 6.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

Egress targets are hardcoded module constants (a mitigating factor), but there is no code-layer allow-list: no frozenset of permitted hosts and no assert_host_allowed()-style pre-request check before outbound calls, and no docs/network-egress.md.

### Expected Behavior

A frozenset allow-list in code plus a pre-request assert_host_allowed() before every outbound request, documented in docs/network-egress.md.

### Evidence

- `src/swiss_housing_mcp/gwr.py:30-31` — hosts hardcoded but not centralised into an enforced allow-list
- `src/swiss_housing_mcp/gwr.py:77,142,190,202` — outbound GETs with no host allow-list check

### Risk Description

A future bug or feature constructing a URL from a variable could reach an unintended host with nothing to stop it; the hardcoded constants are a convention, not an enforced control.

### Remediation

Add ALLOWED_HOSTS = frozenset({'public.madd.bfs.admin.ch','api3.geo.admin.ch'}) and call assert_host_allowed(url) at the top of fetch_with_retry; document in docs/network-egress.md.

### Effort Estimate

**S**

### Dependencies / Blockers

Pairs with SEC-004 (SSRF guard)

### Verification After Fix

- Re-run the `SEC-021` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
