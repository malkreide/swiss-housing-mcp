# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Frischehinweise auf `tools/list` und `server/discover`** (SEP-2549, Spec
  `2026-07-28`): `ttlMs` 300000, `cacheScope` `public`. Das SDK setzt beides von
  sich aus auf «sofort veraltet, nie geteilt» — wer nichts übergibt, verhält
  sich also nicht neutral, sondern lässt jeden Client bei jeder Verbindung neu
  auflisten, für eine Liste, die beim Import feststeht und für jeden Aufrufer
  dieselbe ist. `prompts/list` und `resources/list` bleiben ungesetzt: dieser
  Server registriert weder das eine noch das andere.

- **Protokoll-Gate: beide Spec-Aeren gepinnt und geprueft**
  (`tests/test_protocol_version.py`). `mcp` 2.x bedient zwei Aeren ueber
  denselben Server — den `initialize`-Handshake, der bei `2025-11-25`
  deckelt, und den Pro-Request-Envelope, der `2026-07-28` erreicht.
  `LATEST_PROTOCOL_VERSION` ist ein Alias auf die **moderne** Aera; wer nur
  dagegen pinnt, laesst genau die Aera frei wandern, die heutige Clients
  aushandeln. Beide sind jetzt einzeln gepinnt, ein Dependabot-Bump von
  `mcp` kann keine davon still verschieben.

  Ohne gemessenen Teil: dieser Server baut keine ASGI-App, durch die sich ein
  `initialize` schicken liesse. Das Gate haengt deshalb an den SDK-Konstanten —
  die schwaechere Form, im Docstring benannt statt verschwiegen.

  Beide READMEs beschreiben die Aeren; ein Test haelt jede Sprache einzeln
  dagegen — im Portfolio sind EN und DE desselben Repos schon dreimal
  auseinandergelaufen, weil nur eine Fassung nachgezogen wurde.

### Added

- **Die Pruefsummen im Fixture-Nachweis waren Zierde.** `PROVENANCE.md` fuehrt
  je Datei einen SHA-256 — um genau einen Fall zu fangen: eine Aufzeichnung,
  die nach dem Lauf von Hand nachgebessert wurde. Eine korrigierte Antwort ist
  wieder eine erfundene, und von aussen ist ihr das nicht anzusehen.
  Nachgerechnet hat sie kein Test. `test_die_pruefsumme_im_nachweis_stimmt`
  tut es jetzt, ueber die Bytes auf der Platte statt ueber den Loader — genau
  die hat der Recorder gehasht.

- **Aufgezeichnete Fixtures, eine je externem Endpunkt, mit Nachweis.**
  `tests/fixtures/` haelt jetzt echte Antworten aller drei Endpunkte: den
  GWR-Dump von `public.madd.bfs.admin.ch` sowie `SearchServer` und
  `MapServer/find` von `api3.geo.admin.ch`. Herkunft, Datum, Auswahlregel und
  SHA-256 je Datei in `tests/fixtures/PROVENANCE.md`, geladen ueber
  `tests/fixture_data.py`.

  Der GWR-Dump ist der besondere Fall: die Quelle liefert kein JSON, sondern ein
  ZIP mit einer SQLite-Datenbank, die der Server per SQL abfragt. Die
  Aufzeichnung uebernimmt die `CREATE`-Anweisungen **wortgleich** — ein
  nachgebautes Schema waere wieder eine Annahme — und fuellt sie mit einem
  Gebaeude samt seinen Eingaengen und Wohnungen; `code` und `_metadata`
  vollstaendig. 18 kB statt 3.4 MB, die 47 Spalten von `building` unberuehrt.

  Beide geo.admin-Aufzeichnungen zeigen dasselbe Gebaeude wie der Dump. Zwei
  erfundene Fixtures haetten hier leicht zwei verschiedene gezeigt.

  Gegenprobe: Aufnahmedatum entfernt -> Datums-Check faellt; Spalte im Dump
  umbenannt -> Schema- und Entpack-Test fallen; Wohnungen geleert ->
  Zusammenhangs-Test faellt; EGID bei geo.admin geaendert -> der
  Quellen-Abgleich faellt.

### Changed

- **Der Backoff-Schlaf wird ueber einen Modul-Alias gepatcht, nicht ueber
  `asyncio.sleep`.** Die Tests nullten die Wartezeit mit
  `monkeypatch.setattr(<modul>.asyncio, "sleep", ...)`. Das liest sich lokal,
  ersetzt `sleep` aber auf dem geteilten Modulobjekt — fuer httpx, respx,
  pytest-asyncio und jeden anderen Importeur im Prozess. Das Modul legt die
  Naht jetzt als `_sleep = asyncio.sleep` offen; gepatcht wird diese.
  `test_der_retry_geht_ueber_den_alias` haelt sie: umgeht der Retry den Alias,
  faellt der Test in Sekundenbruchteilen. Ohne ihn fiel gar nichts — die Suite
  wurde nur ein Vielfaches langsamer, und eine laengere Laufzeit ist kein
  Signal, das jemand liest.

### Fixed
- **`fetch_with_retry` had six defects, all inherited from the shared
  template.** `gwr.py` copied the `mcp-data-source-probe` reference retry, and
  the template shipped these until 2026-08-07. A sweep across eleven servers
  found that none read `Retry-After` and none jittered — one template, eleven
  copies, not eleven independent omissions.
  1. **No jitter.** `2 ** attempt` is deterministic, so every client that hit
     the same outage retried in lockstep and returned as a wave exactly when
     the source recovered. Now spread into `[0.5x, 1.5x]`.
  2. **`Retry-After` was never read.** A 429 or 503 answers the very question
     the backoff curve guesses at. Both RFC 9110 §10.2.3 forms are now read
     (delta-seconds and HTTP-date); an unparseable header yields `None` and
     falls back to the curve — it must never crash on the error path. The
     jitter on top is one-sided `[1.0x, 1.25x]`: the source said *when*, so
     later is polite and earlier ignores the value just read.
  3. **No cap on a single wait**, and the cap is now applied *after* the
     jitter. `min(cap, base) * jitter` and `min(cap, base * jitter)` both
     contain a cap and a jitter; only the second is bounded — 20s times 1.5 is
     30s.
  4. **The budget counted attempts, not seconds.** Four attempts against an
     upstream that takes 30s to time out is two minutes inside one tool call.
     Now 25s for the whole call, anchored on the MCP SDK's
     `MCP_DEFAULT_TIMEOUT = 30.0`.
  5. **Nothing held that budget.** It is now an `asyncio.timeout` wall-clock
     deadline, not an httpx timeout: httpx bounds each *operation*, and its
     read timeout restarts with every chunk, so a slowly trickling response
     outlived the budget without any single read expiring.
  6. **The error was wrapped.** `raise RuntimeError(f"Upstream unreachable
     after retries: {last_error}")` — and `httpx.ConnectTimeout`, `ReadTimeout`
     and `ConnectError` all carry an **empty** `str()`. Those are the only
     errors a real outage produces, so the message stopped at the colon,
     naming neither the failure mode nor the host. The original exception is
     now re-raised: callers keep the type and `.response`. The one case with no
     original — budget spent before a request went out — raises the named
     `UpstreamUnavailableError` rather than a bare `RuntimeError` that a caller
     cannot tell apart from a bug in this server.

  **A test pinned the defect.** `test_network_error_raises_runtime_error`
  asserted `RuntimeError, match="Upstream unreachable"`, so the wrapper could
  not be removed without it going red. Its mock passed `"boom"` as the message,
  which is exactly what made it misleading — informative in the test, blank in
  production. It now asserts that the original exception type travels out, and
  a second test covers the empty-`str()` case directly. Three further tests
  cover `Retry-After` (both forms plus the refusal cases), the jitter spread,
  and that the cap binds after jittering.

- **MCP Registry publish blockers**, both caught before the first release:
  - `server.json` `description` was 172 characters; the registry rejects
    anything over 100 with a `422`. Shortened to 97, keeping the official
    register name, the `GWR/RegBL` identifiers and the `EGID`/`EWID` lookup
    keys.
  - The registry verifies ownership of a PyPI package via an
    `mcp-name: <server-name>` marker in the published package README; it was
    missing. Added as an HTML comment at the end of `README.md` (the package
    `long_description`), matching the placement used by the sibling servers.

  Because this server has not been published yet, both fixes land before the
  first release and need no version bump.

### Security
- **SEC-016 (0.0.0.0 binding / NeighborJack):** the HTTP transports defaulted
  `HOST` to `0.0.0.0`, binding all interfaces. Now default to `127.0.0.1`;
  exposing all interfaces requires an explicit `HOST=0.0.0.0`.

### Added
- Portfolio-standard repository files, aligning the repo with the sibling
  `*-mcp` servers: `.github/workflows/ci.yml` (test/lint/live) and `publish.yml`
  (OIDC PyPI + MCP Registry, tag-guarded version derivation),
  `CONTRIBUTING.md`/`.de.md`, `SECURITY.md`/`.de.md`, `EXAMPLES.md`, and
  `server.json` (MCP Registry manifest)

### Changed
- `pyproject.toml` aligned to portfolio standards: `requires-python >=3.11`,
  `mcp[cli]` upper-bounded (`<2.0.0`), `testpaths`, and a `Changelog` project URL
- `ruff format` applied to `src/` (formatting only, no behaviour change)

## [0.1.0] - 2026-07-24

### Added
- Initial release with 9 tools: `lookup_building`, `address_to_egid`,
  `lookup_dwellings`, `new_construction`, `construction_pipeline`,
  `buildings_in_bbox`, `municipality_housing_stats`, `explain_code`,
  `dump_status`
- Architecture B (Hybrid: Dump-first, API-fallback), verified live 2026-07-24
- Dual transport: stdio (Claude Desktop) + streamable-http/SSE (cloud)
- Retry with exponential backoff, provenance envelope in every response

### Known findings
- geo.admin.ch answers HTTP 200 with an empty `results` array for unknown
  EGIDs — an empty array is a soft "not found", not an upstream error.
- The public MADD dump ships a ready-made `data.sqlite` (building, entrance,
  dwelling, code) — no CSV parsing needed. Refreshed daily around 05:30 CET.
- SearchServer geocoding returns `featureId` as `{EGID}_{EDID}` — address
  geocoding and register lookup in one call. Note the axis swap: `y` = LV95
  east, `x` = LV95 north.
