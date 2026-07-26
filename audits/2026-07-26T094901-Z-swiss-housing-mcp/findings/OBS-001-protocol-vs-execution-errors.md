## Finding: OBS-001 — Protocol vs. Execution Errors: korrekte Trennung

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `OBS-001` |
| **PDF-Reference** | Sec 3.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

Execution-error paths are exercised at the client layer (unknown canton -> ValueError, 4xx no-retry, network error -> RuntimeError) and FastMCP converts raised exceptions into isError tool results by default. But handlers do not explicitly catch/classify app errors, and there is no protocol-error (wrong tool / bad args) test.

### Expected Behavior

Handlers catch app-specific errors and return them as isError tool-results; at least one execution-error and one protocol-error test are documented.

### Evidence

- `tests/test_server.py:123-127` — unknown-canton ValueError path
- `tests/test_server.py:99-118` — 4xx / network-error paths (client layer, not tool layer)

### Risk Description

Reliance on the framework default means an unexpected exception type could surface as a raw JSON-RPC error rather than a graceful isError, and the protocol-error path is unverified.

### Remediation

Add explicit try/except in tool handlers returning structured isError payloads; add a test that calls a tool with invalid args and asserts a protocol-level error.

### Effort Estimate

**M**

### Dependencies / Blockers

Relates to OBS-002 (error masking)

### Verification After Fix

- Re-run the `OBS-001` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
