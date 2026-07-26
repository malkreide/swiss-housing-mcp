## Finding: SEC-004 — SSRF-Prevention: HTTPS-Enforcement + IP-Blocklisting

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `SEC-004` |
| **PDF-Reference** | Sec 6.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

Outbound hosts are hardcoded HTTPS constants and user input flows only into query parameters, not the host — so the SSRF surface is minimal. But there is no explicit https-scheme validation, no resolved-IP blocklist (private/link-local/loopback), and no block of the cloud-metadata IP 169.254.169.254.

### Expected Behavior

Validate the https scheme and check the resolved IP against a blocklist (private/link-local/loopback + 169.254.169.254 + ::1/fe80::) before each outbound request.

### Evidence

- `src/swiss_housing_mcp/gwr.py:30-31` — MADD_BASE/GEOADMIN_BASE fixed https constants
- `src/swiss_housing_mcp/gwr.py:186-203` — user text only in query params, never the host

### Risk Description

Low today, but if a future tool ever accepts a caller-supplied URL/host, the absence of a scheme/IP guard would immediately expose SSRF to cloud metadata endpoints.

### Remediation

Add an assert_url_allowed() helper enforcing https + resolved-IP blocklist, called from fetch_with_retry; wire it together with the SEC-021 allow-list.

### Effort Estimate

**M**

### Dependencies / Blockers

Pairs with SEC-021 (egress allow-list) and SEC-005

### Verification After Fix

- Re-run the `SEC-004` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
