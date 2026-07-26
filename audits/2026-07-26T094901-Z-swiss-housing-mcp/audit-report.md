# MCP-Server Audit-Report — `swiss-housing-mcp`

**Audit-Datum:** 
**Skill-Version:** 1.0.0
**Catalog-Version:** ?

---

## 1. Executive Summary

Server `swiss-housing-mcp` wurde gegen 32 anwendbare Best-Practice-Checks geprüft. 11 bestanden, 21 Findings dokumentiert (4 critical, 11 high, 6 medium, 0 low). Production-Readiness: erreicht.

**Production-Readiness:** YES

---

## 2. Profil-Snapshot

| Feld | Wert |
|---|---|
| Server-Name | `swiss-housing-mcp` |
| Audit-Datum | ? |
| Skill-Version | 1.0.0 |
| Catalog-Version | ? |

---

## 3. Applicability

### Status pro Kategorie

| Kategorie | Pass | Fail | Partial | Todo | N/A |
|---|---|---|---|---|---|
| ARCH | 5 | 0 | 6 | 0 | 0 |
| CH | 1 | 0 | 0 | 0 | 0 |
| OBS | 0 | 0 | 4 | 0 | 0 |
| OPS | 0 | 0 | 3 | 0 | 0 |
| SCALE | 0 | 0 | 1 | 0 | 0 |
| SEC | 5 | 0 | 7 | 0 | 0 |
| **Total** | **11** | **0** | **21** | **0** | **0** |

---

## 4. Findings-Übersicht

_Policy: `fail-or-partial`_

| ID | Category | Severity | Status |
|---|---|---|---|
| OBS-004 | OBS | critical | partial |
| SEC-004 | SEC | critical | partial |
| SEC-009 | SEC | critical | partial |
| SEC-019 | SEC | critical | partial |
| ARCH-004 | ARCH | high | partial |
| ARCH-009 | ARCH | high | partial |
| OBS-001 | OBS | high | partial |
| OBS-002 | OBS | high | partial |
| OPS-001 | OPS | high | partial |
| OPS-003 | OPS | high | partial |
| SCALE-002 | SCALE | high | partial |
| SEC-005 | SEC | high | partial |
| SEC-007 | SEC | high | partial |
| SEC-018 | SEC | high | partial |
| SEC-021 | SEC | high | partial |
| ARCH-002 | ARCH | medium | partial |
| ARCH-003 | ARCH | medium | partial |
| ARCH-008 | ARCH | medium | partial |
| ARCH-012 | ARCH | medium | partial |
| OBS-003 | OBS | medium | partial |
| OPS-002 | OPS | medium | partial |

**Gesamt:** 21 Findings

---

## 5. Detail-Findings

### ARCH-002

## Finding: ARCH-002 — Tool-Beschreibung mit Use-Case-Tags

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `ARCH-002` |
| **PDF-Reference** | Sec 2.2 |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

All 9 tool docstrings are multi-sentence and give real prose context (e.g. server.py:177-179 explains the 4+ room share as a family-housing proxy), but none uses structured `<use_case>` / `<important_notes>` / `<example>` tags.

### Expected Behavior

At least 80% of tools carry a structured use-case tag (or equivalent) so the LLM can differentiate semantically similar tools reliably.

### Evidence

- `src/swiss_housing_mcp/server.py:76-81` — lookup_building docstring: prose only, no tags
- `src/swiss_housing_mcp/server.py:225-232` — construction_pipeline docstring: prose only

### Risk Description

With several overlapping stats tools (new_construction, construction_pipeline, municipality_housing_stats, buildings_in_bbox), an LLM may pick the wrong one; prose descriptions are weaker discriminators than explicit tags.

### Remediation

Add `<use_case>` and, where relevant, `<important_notes>` tags to each description string, keeping the existing prose. No behavioural change.

### Effort Estimate

**S**

### Dependencies / Blockers

None

### Verification After Fix

- Re-run the `ARCH-002` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.


### ARCH-003

## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `ARCH-003` |
| **PDF-Reference** | Sec 2.2 |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

Not-found is handled with structured envelopes (BuildingResponse(found=False), dump_status note) rather than bare []/None, which avoids the worst anti-pattern. However there is no fuzzy-match / suggestion fallback and no `match_type` field.

### Expected Behavior

Non-sensitive search tools should, on an empty exact result, return fuzzy/related results or actionable suggestions plus a `match_type` (exact|fuzzy|none) field.

### Evidence

- `src/swiss_housing_mcp/server.py:84-85` — returns BuildingResponse(provenance='live_api', found=False) with no hint
- `src/swiss_housing_mcp/server.py:135` — address_to_egid returns matches list with no fuzzy/suggestion path

### Risk Description

On a typo'd address or unknown EGID the LLM gets found=False with no next step, risking a dead-end or a hallucinated answer instead of a refined retry.

### Remediation

Add a `match_type` field to responses; on empty geocode/lookup results surface near-matches or a hint (e.g. suggest address_to_egid before lookup_building). Public data, so heuristics leak nothing.

### Effort Estimate

**S**

### Dependencies / Blockers

None

### Verification After Fix

- Re-run the `ARCH-003` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.


### ARCH-004

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


### ARCH-008

## Finding: ARCH-008 — Drei Primitive nutzen: Tools, Resources und Prompts

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `ARCH-008` |
| **PDF-Reference** | Anhang A2 |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

The server exposes only Tools; there are no Resources or Prompts, and the README contains no documented justification for the tools-only choice.

### Expected Behavior

Use at least two of the three primitives, OR document in the README why only Tools are used. Idempotent read-only lookups are Resource candidates.

### Evidence

- grep `@mcp.resource`/`@mcp.prompt` in src/ — no matches
- `README.md` / `README.de.md` — grep primitive/resource/prompt returns nothing

### Risk Description

All read-only lookups sit in the tool manifest, inflating token cost per call and forgoing Resource cache/URI benefits; acceptable for a Phase-1 wrapper but undocumented.

### Remediation

Either add a short 'MCP Primitives' README section justifying tools-only for Phase 1, or migrate side-effect-free lookups (dump_status, explain_code) to Resources with a documented URI scheme.

### Effort Estimate

**M**

### Dependencies / Blockers

None

### Verification After Fix

- Re-run the `ARCH-008` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.


### ARCH-009

## Finding: ARCH-009 — Tool Annotations: openWorldHint / idempotentHint vollständig

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `ARCH-009` |
| **PDF-Reference** | Anhang A5 |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

All 9 tools carry explicit annotations and readOnlyHint:True is correct (the server is fully read-only). But openWorldHint is set only on the two live-API tools; the 7 dump-fetching tools omit it despite downloading from upstream. idempotentHint is never set, and there is no annotations table in the docs.

### Expected Behavior

openWorldHint:true on every tool that reaches an external system; idempotentHint set where applicable; an annotations overview in README/docs.

### Evidence

- `src/swiss_housing_mcp/server.py:75,108` — openWorldHint:True (correct, live API)
- `src/swiss_housing_mcp/server.py:138,170,224,267,310,352` — readOnlyHint only, yet these call store.ensure_dump -> gwr.py:142 download from public.madd.bfs.admin.ch

### Risk Description

A host relying on openWorldHint for network-egress warnings would under-warn for the 7 dump tools that do reach the network; inconsistent hints erode the host's ability to reason about egress.

### Remediation

Set openWorldHint:True on all tools whose path calls ensure_dump; add idempotentHint:True (read-only queries are idempotent); publish an annotations table in the README.

### Effort Estimate

**S**

### Dependencies / Blockers

None

### Verification After Fix

- Re-run the `ARCH-009` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.


### ARCH-012

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


### OBS-001

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


### OBS-002

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


### OBS-003

## Finding: OBS-003 — Structured Logging mit RFC 5424 Severity-Stufen

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `OBS-003` |
| **PDF-Reference** | Sec 3.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

There is no logging framework at all (no structlog/loguru/logging), so no severity levels or per-call bound context. There are also no print() statements. SECURITY.md records structured logging as an accepted risk for the stdio profile.

### Expected Behavior

A structured logger (structlog/loguru) emitting JSON/logfmt with >=4 severity levels and per-tool-call bound context.

### Evidence

- grep structlog/loguru/logging/print in src/ — no logging framework and no print()
- `SECURITY.md:53-56` — 'Structured logging: accepted risk' for the stdio profile

### Risk Description

No observability: a failing dump download or upstream error leaves no trace for the operator; acceptable for local stdio but blocks any cloud/SSE move.

### Remediation

Add structlog with a stderr WriteLoggerFactory (see OBS-004); bind tool name + correlation id per call; keep it off stdout.

### Effort Estimate

**M**

### Dependencies / Blockers

Pairs with OBS-004 (stderr sink)

### Verification After Fix

- Re-run the `OBS-003` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.


### OBS-004

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


### OPS-001

## Finding: OPS-001 — Test-Strategie: Unit-Tests mocked + Live-Tests gemarkert

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `OPS-001` |
| **PDF-Reference** | Sec 4.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

The test architecture is exemplary: respx-mocked units, a registered `live` marker, CI running `pytest -m 'not live'`, and a separate nightly live job. Coverage, however, is thin: 7 unit + 2 live tests for 9 tools, and they exercise the gwr client layer only — the 9 @mcp.tool handlers are not directly tested.

### Expected Behavior

>=5 unit tests and >=1 live test per tool, covering the tool handlers (not just the client helpers).

### Evidence

- `tests/test_server.py:38-46` — respx-mocked unit test (client layer)
- `pyproject.toml:52-54` — live marker registered; `.github/workflows/ci.yml:42-46` runs pytest -m 'not live'; ci.yml:64-82 nightly live job
- `tests/test_server.py` — 7 not-live + 2 live tests total for 9 tools

### Risk Description

The SQL-heavy aggregation tools (new_construction, construction_pipeline, buildings_in_bbox, municipality_housing_stats) have no tests; a regression in a JOIN or GROUP BY would ship undetected.

### Remediation

Add handler-level tests with a seeded in-memory/temp SQLite dump for each aggregation tool; add one live test per tool.

### Effort Estimate

**M**

### Dependencies / Blockers

None

### Verification After Fix

- Re-run the `OPS-001` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.


### OPS-002

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


### OPS-003

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


### SCALE-002

## Finding: SCALE-002 — Stateful Load Balancing für Streamable HTTP / SSE

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `SCALE-002` |
| **PDF-Reference** | Sec 5.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

The streamable-http/sse transports exist (dual), but there is no sticky-session or shared-state (Redis/Durable-Objects) session manager and no defined session TTL. The server is not currently cloud-deployed (profile is_cloud_deployed=false).

### Expected Behavior

Sticky sessions at the LB keyed on Mcp-Session-Id, or a shared-state session manager, with an explicit session TTL, before horizontal scaling.

### Evidence

- `src/swiss_housing_mcp/__main__.py:12-20` — streamable-http/sse selectable, single-process
- profile.yaml — is_cloud_deployed: false, deployment: [local-stdio]

### Risk Description

If the HTTP transport is ever run behind more than one replica, session-bound requests would land on the wrong instance and fail; latent until a cloud move.

### Remediation

Document a single-instance constraint for the HTTP transport now; add sticky-session/Redis session state before any multi-replica deployment.

### Effort Estimate

**M**

### Dependencies / Blockers

Blocked-until: cloud deployment decision

### Verification After Fix

- Re-run the `SCALE-002` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.


### SEC-004

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


### SEC-005

## Finding: SEC-005 — DNS-Rebinding-Prevention: DNS-Pinning gegen TOCTOU

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `SEC-005` |
| **PDF-Reference** | Sec 6.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

Each request is a single httpx GET against fixed public hosts with no user-controlled hostname, so rebinding risk is low. There is no DNS-pinning / single-resolution guard.

### Expected Behavior

Resolve DNS once and pin the resolved IP for the connection while keeping the original hostname for SNI/Host and cert validation.

### Evidence

- `src/swiss_housing_mcp/gwr.py:70-86` — fetch_with_retry issues plain httpx.get against fixed hosts

### Risk Description

A rebinding attacker controlling DNS for the upstream host could in theory swap the IP between resolution and connect; residual risk is low because hosts are fixed federal endpoints.

### Remediation

If/when SEC-004 is implemented, pin the resolved IP via a custom transport/resolver; otherwise accept-risk with a documented note given fixed public hosts.

### Effort Estimate

**M**

### Dependencies / Blockers

Depends on SEC-004

### Verification After Fix

- Re-run the `SEC-005` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.


### SEC-007

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


### SEC-009

## Finding: SEC-009 — Session-ID Cryptographic Binding

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `SEC-009` |
| **PDF-Reference** | Sec 6.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

auth_model is none and there is no custom session code; session-id handling for the HTTP transport is delegated to the FastMCP SDK default. No explicit user<->session binding, TTL, or invalidation is asserted in code.

### Expected Behavior

Session IDs generated with >=128-bit entropy, cryptographically bound to a validated user identity, with explicit TTL and server-side invalidation.

### Evidence

- profile.yaml — auth_model: none; `src/swiss_housing_mcp/server.py:36` — FastMCP with no session customisation
- no OAuth/user identity in the codebase (public, anonymous, read-only)

### Risk Description

Low for an anonymous read-only public-data server (no per-user data to protect), but if auth is ever added the HTTP transport has no session-binding scaffold and would need it from scratch.

### Remediation

Keep HTTP transport as a documented opt-in for trusted networks now; if multi-tenant auth is added, implement signed session tokens binding user_id:session_id with TTL and logout invalidation.

### Effort Estimate

**L**

### Dependencies / Blockers

Blocked-until: an auth model is introduced

### Verification After Fix

- Re-run the `SEC-009` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.


### SEC-018

## Finding: SEC-018 — Input-Validation an Tool-Boundaries

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `SEC-018` |
| **PDF-Reference** | Sec 6.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

Response models use Pydantic v2 and tool inputs are type-hinted (so FastMCP applies type-level validation), and canton is whitelist-checked. But tool-input fields carry no value constraints: no ge/le on numerics, no min/max_length on the address string, and no strict/extra=forbid. The README's claim of range-checked EGID/coordinates is not enforced in code.

### Expected Behavior

All tool arguments validated with ge/le on numerics, min/max_length (+ pattern) on strings, strict=True and extra='forbid'.

### Evidence

- `src/swiss_housing_mcp/server.py:76` — egid:int with no bounds; server.py:109 limit:int with no ge/le; server.py:268-274 LV95 floats unbounded
- `src/swiss_housing_mcp/gwr.py:130-131` — canton whitelist-checked (the one enforced constraint)
- `SECURITY.md:30` — claims EGID/EWID and LV95 are range-checked (not matched by code)

### Risk Description

Unbounded inputs allow, e.g., a huge `limit` or absurd bbox to hit upstream/SQLite unnecessarily; the doc/code mismatch also misleads auditors about the actual control.

### Remediation

Introduce Pydantic Field constraints (ge/le for EGID/BFS/year/limit/LV95 ranges, max_length for address) on tool args, or Annotated types; set strict where feasible. Align SECURITY.md with the real state.

### Effort Estimate

**S**

### Dependencies / Blockers

Relates to OBS-001 (validation errors as isError)

### Verification After Fix

- Re-run the `SEC-018` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.


### SEC-019

## Finding: SEC-019 — Lethal Trifecta vermeiden: Server-Separation

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `swiss-housing-mcp` |
| **Check-Reference** | `SEC-019` |
| **PDF-Reference** | Sec 6.x |
| **Audit-Datum** | 2026-07-26 |
| **Auditor** | Claude Opus 4.8 (mcp-audit skill v1.0.0) |

### Observed Behavior

The server is fully read-only, egress is confined to fixed BFS/geo.admin.ch hosts with no arbitrary send/exfiltration path, and the data is public — so it holds at most 2 of the 3 trifecta capabilities. This structural safety is real but is not documented as an assessed decision (no trifecta ADR).

### Expected Behavior

A documented trifecta assessment confirming <=2 of the 3 capabilities, with recipient allow-lists as frozensets if any send capability exists.

### Evidence

- `src/swiss_housing_mcp/server.py` — all 9 tools read-only; `gwr.py:30-31` egress to fixed hosts only
- `SECURITY.md:32` — documents the no-write / read-only posture (but not framed as a trifecta assessment)

### Risk Description

Structurally safe today, but without a written assessment a future contributor could add a send-capable tool (webhook/mail) without realising it completes the trifecta.

### Remediation

Add a short 'Lethal Trifecta' assessment to SECURITY.md/docs recording the <=2-capability status and the rule that any send capability requires a frozenset allow-list + sign-off.

### Effort Estimate

**S**

### Dependencies / Blockers

None

### Verification After Fix

- Re-run the `SEC-019` check against the repo (`eval_applicability` + manual verification).
- Add/extend a test or grep-guard that asserts the anti-pattern is gone.


### SEC-021

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


---

## 6. Remediation-Plan

### Empfohlene Reihenfolge

1. **OBS-004** (critical, partial)
2. **SEC-004** (critical, partial)
3. **SEC-009** (critical, partial)
4. **SEC-019** (critical, partial)
5. **ARCH-004** (high, partial)
6. **ARCH-009** (high, partial)
7. **OBS-001** (high, partial)
8. **OBS-002** (high, partial)
9. **OPS-001** (high, partial)
10. **OPS-003** (high, partial)
11. **SCALE-002** (high, partial)
12. **SEC-005** (high, partial)
13. **SEC-007** (high, partial)
14. **SEC-018** (high, partial)
15. **SEC-021** (high, partial)
16. **ARCH-002** (medium, partial)
17. **ARCH-003** (medium, partial)
18. **ARCH-008** (medium, partial)
19. **ARCH-012** (medium, partial)
20. **OBS-003** (medium, partial)
21. **OPS-002** (medium, partial)

---

## 7. Audit-Metadata

| Feld | Wert |
|---|---|
| skill_version | `1.0.0` |
| policy | `fail-or-partial` |


_Generated by tools/build_report.py — do not edit by hand._
