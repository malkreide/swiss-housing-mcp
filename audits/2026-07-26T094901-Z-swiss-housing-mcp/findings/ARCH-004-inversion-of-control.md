## Finding: ARCH-004 — Inversion of Control: Transport-agnostische Server-Logik

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `ARCH-004` |
| **PDF-Reference** | Sec 2.1 |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

Tool handlers are transport-agnostic (typed args, no request/stdin/stdout access) and dual transport is selectable via env var. But configuration is read through scattered os.environ.get calls rather than a Settings object, and there is no shared lifespan; the httpx client is recreated per call.

### Expected Behavior

Configuration via a Pydantic BaseSettings object and a shared lifespan for cross-transport setup (e.g. one pooled httpx client).

### Evidence

- `src/swiss_housing_mcp/__main__.py:13-19` — os.environ.get for transport/host/port inline
- `src/swiss_housing_mcp/gwr.py:34-37` — CACHE_DIR / DUMP_TTL_HOURS read from os.environ at module scope
- `src/swiss_housing_mcp/server.py:54-55` — new httpx.AsyncClient per tool call

### Risk Description

Module-scope env reads make tests order-sensitive and per-call client creation drops connection reuse; not a security bug but a maintainability/testability drag as the server grows.

### Remediation

Introduce a Settings(BaseSettings) object and a FastMCP lifespan that owns a shared AsyncClient; inject via ctx/state.

### Effort Estimate

**M**

### Dependencies / Blockers

None

### Verification After Fix

- Re-run the `ARCH-004` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.
