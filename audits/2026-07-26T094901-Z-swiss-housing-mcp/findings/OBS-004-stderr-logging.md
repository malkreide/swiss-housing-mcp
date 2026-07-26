## Finding: OBS-004 — stderr für stdio-Server: stdout reserviert für Protocol

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `OBS-004` |
| **PDF-Reference** | Sec 3.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

No print()/stdout writes exist anywhere in src/, so the JSON-RPC stream is not polluted and the core OBS-004 risk is avoided. However there is no explicit stderr-pinned logging configuration; the guarantee rests on the current absence of any logging rather than an enforced stderr sink.

### Expected Behavior

Logging explicitly directed to sys.stderr (e.g. logging.basicConfig(stream=sys.stderr) or structlog WriteLoggerFactory(file=sys.stderr)), so future log lines can never reach stdout.

### Evidence

- grep print(/console.log in src/ — none (stdout clean today)
- grep basicConfig/stream=sys.stderr in src/ — none (no explicit stderr config)

### Risk Description

The moment any contributor adds a print() or a default-config logger, it would write to stdout and corrupt the JSON-RPC framing for stdio clients (Claude Desktop) — a latent, easily-triggered break.

### Remediation

Add a logging setup pinned to sys.stderr at startup and a CI grep-guard forbidding print( in src/, so stdout stays reserved for the protocol.

### Effort Estimate

**S**

### Dependencies / Blockers

None

### Verification After Fix

- Re-run the `OBS-004` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
