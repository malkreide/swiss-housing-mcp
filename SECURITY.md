# Security Policy & Posture

[🇩🇪 Deutsche Version](SECURITY.de.md)

`swiss-housing-mcp` follows the same security profile as the rest of the
[Swiss Public Data MCP Portfolio](https://github.com/malkreide): a **read-only**,
**no-PII**, **public-open-data** MCP server. It exposes the Swiss Federal Register
of Buildings and Dwellings (GWR/RegBL) — building and dwelling attributes, not
personal data. This document records the security posture and the
**accepted-risk** decisions for controls deliberately deferred for this profile.

## Reporting a vulnerability

Please open a private security advisory on the GitHub repository, or contact the
maintainer listed in `README.md`. Do not file public issues for exploitable
vulnerabilities.

## Posture summary

All tools only **query** upstream — there is no write path, no authentication,
and no personal data. Upstream is the public GWR/RegBL infrastructure
(`public.madd.bfs.admin.ch` cantonal dumps) and `api3.geo.admin.ch` for
single-entity lookups.

| Area | Control |
|---|---|
| Egress | HTTPS-only to the public BFS / geo.admin.ch hosts |
| TLS | Certificate verification on by default (httpx default; never disabled) |
| Transport | stdio by default — stdout reserved for the JSON-RPC stream; HTTP transports bind to loopback (`127.0.0.1`) unless `HOST=0.0.0.0` is set explicitly (SEC-016) |
| Input | Pydantic v2 validation on tool inputs; EGID/EWID and LV95 coordinates are range-checked |
| Secrets | No API keys or credentials — the GWR/RegBL sources are public, so there is nothing to store or leak |
| Write | None — read-only register access; the spatial layer lives in `swiss-geodata-mcp` |
| Tests | respx-mocked unit suite on every PR (3.11/3.12/3.13); live tests gated to a nightly job |

> **Hardening & audit status:** the formal MCP best-practice audit has been run —
> see [`audits/2026-07-26T094901-Z-swiss-housing-mcp/`](audits/2026-07-26T094901-Z-swiss-housing-mcp/)
> (skill v1.0.0, 32 applicable checks). Scorecard: **11 pass / 21 partial / 0 fail**,
> **production-ready: yes** (no critical/high failures). The partials are hardening
> follow-ups, not blockers: a code-layer egress allow-list (`assert_host_allowed`,
> SEC-021), an explicit stderr-pinned logging setup (OBS-004), `mask_error_details`
> (OBS-002), and tool-input value constraints (SEC-018) are present in sibling
> servers such as `swiss-geodata-mcp` and `swiss-snb-mcp` and are tracked here as
> open findings in the audit run above.

## Accepted risks

The following controls are deliberately **out of scope** for a stdio-first
public-open-data server. None has a security impact for this profile.

### Container sandboxing

**Status:** accepted risk. No `Dockerfile`. Acceptable for local-stdio
public-data servers; ship a hardened image if the deployment profile moves to
the cloud.

### Structured logging

**Status:** accepted risk. Plain logging is sufficient for a stdio server;
revisit under a centralised log pipeline (cloud/SSE).

## Re-evaluation triggers

Revisit these acceptances if the server ever:

- gains **write** capability or starts processing **PII**, or
- registers tools **dynamically** / from remote sources, or
- is moved to a **cloud / SSE** deployment, or
- is aggregated behind a shared MCP gateway (then implement gateway-level tool
  allow-listing and poisoning detection there).
