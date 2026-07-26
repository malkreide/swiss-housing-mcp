## Finding: OBS-002 — Mask Error Details: keine Stacktraces / Upstream-Bodies ans LLM

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `OBS-002` |
| **PDF-Reference** | Sec 3.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

FastMCP is initialised without mask_error_details, and gwr.py embeds the upstream exception string into a RuntimeError that reaches the tool result. No stacktrace or SQL is dumped, but there is no sanitisation layer.

### Expected Behavior

mask_error_details=True (or equivalent), user-friendly execution-error messages, and original errors confined to server logs.

### Evidence

- grep mask_error_details in src/ — no match; `src/swiss_housing_mcp/server.py:36` FastMCP('swiss-housing-mcp') uses default
- `src/swiss_housing_mcp/gwr.py:86` — RuntimeError(f'Upstream unreachable after retries: {last_error}') leaks upstream error text
- `src/swiss_housing_mcp/gwr.py:153` — FileNotFoundError exposes cache path

### Risk Description

Upstream error text and local cache paths can surface to the LLM/user, a minor information-disclosure and a confusing UX; a future traceback-leaking dependency would go unmasked.

### Remediation

Set mask_error_details=True on FastMCP; wrap upstream/sqlite failures in generic user-facing messages and log the detail to stderr only.

### Effort Estimate

**S**

### Dependencies / Blockers

None

### Verification After Fix

- Re-run the `OBS-002` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
