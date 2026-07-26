# Sicherheitsrichtlinie & Sicherheitslage

[🇬🇧 English Version](SECURITY.md)

`swiss-housing-mcp` folgt demselben Sicherheitsprofil wie das übrige
[Swiss Public Data MCP Portfolio](https://github.com/malkreide): ein **rein
lesender**, **PII-freier** MCP-Server für **öffentliche Open Data**. Er stellt das
Eidgenössische Gebäude- und Wohnungsregister (GWR/RegBL) bereit — Gebäude- und
Wohnungsmerkmale, keine Personendaten. Dieses Dokument hält die Sicherheitslage
fest sowie die **akzeptierten Risiken** für bewusst zurückgestellte Kontrollen.

## Schwachstelle melden

Bitte eröffnen Sie ein privates Security Advisory im GitHub-Repository oder
kontaktieren Sie die in `README.md` genannte verantwortliche Person. Erstellen Sie
für ausnutzbare Schwachstellen **keine** öffentlichen Issues.

## Zusammenfassung der Sicherheitslage

Alle Tools **fragen** Upstream nur ab — kein Schreibpfad, keine Authentifizierung,
keine Personendaten. Upstream ist die öffentliche GWR/RegBL-Infrastruktur
(`public.madd.bfs.admin.ch`, Kantons-Dumps) und `api3.geo.admin.ch` für
Einzelabfragen.

| Bereich | Kontrolle |
|---|---|
| Egress | HTTPS-only zu den öffentlichen BFS-/geo.admin.ch-Hosts |
| TLS | Zertifikatsprüfung standardmässig aktiv (httpx-Standard; nie deaktiviert) |
| Transport | Standardmässig stdio — stdout für den JSON-RPC-Stream reserviert; HTTP-Transporte binden an Loopback (`127.0.0.1`), ausser `HOST=0.0.0.0` wird explizit gesetzt (SEC-016) |
| Input | Pydantic-v2-Validierung der Tool-Inputs; EGID/EWID und LV95-Koordinaten werden bereichsgeprüft |
| Secrets | Keine API-Keys oder Zugangsdaten — die GWR/RegBL-Quellen sind öffentlich, es gibt nichts zu speichern oder zu leaken |
| Schreiben | Keines — rein lesender Registerzugriff; die Raum-Schicht liegt in `swiss-geodata-mcp` |
| Tests | respx-mockierte Unit-Suite bei jedem PR (3.11/3.12/3.13); Live-Tests auf einen Nightly-Job beschränkt |

> **Härtungs- & Audit-Status:** Das formale MCP-Best-Practice-Audit wurde
> durchgeführt — siehe [`audits/2026-07-26T094901-Z-swiss-housing-mcp/`](audits/2026-07-26T094901-Z-swiss-housing-mcp/)
> (Skill v1.0.0, 32 anwendbare Checks). Scorecard: **11 pass / 21 partial / 0 fail**,
> **production-ready: ja** (keine Critical-/High-Fails). Die Partials sind
> Härtungs-Follow-ups, keine Blocker: eine Egress-Allow-List auf Code-Ebene
> (`assert_host_allowed`, SEC-021), ein auf stderr fixiertes Logging (OBS-004),
> `mask_error_details` (OBS-002) und Wertebereichs-Constraints auf Tool-Inputs
> (SEC-018) sind in Geschwister-Servern wie `swiss-geodata-mcp` und `swiss-snb-mcp`
> vorhanden und werden hier als offene Findings im obigen Audit-Run geführt.

## Akzeptierte Risiken

Die folgenden Kontrollen sind für einen stdio-first-Public-Open-Data-Server
bewusst **out of scope**. Keine hat einen Sicherheits-Impact für dieses Profil.

### Container-Sandboxing

**Status:** akzeptiertes Risiko. Kein `Dockerfile`. Akzeptabel für lokale
stdio-Public-Data-Server; ein gehärtetes Image ausliefern, falls sich das
Deployment-Profil in die Cloud verschiebt.

### Strukturiertes Logging

**Status:** akzeptiertes Risiko. Einfaches Logging genügt für einen stdio-Server;
neu zu bewerten unter einer zentralen Log-Pipeline (Cloud/SSE).

## Re-Evaluierungs-Auslöser

Diese Akzeptanzen sollten neu bewertet werden, falls der Server jemals:

- **Schreib**-Funktionalität erhält oder beginnt, **PII** zu verarbeiten, oder
- Tools **dynamisch** / aus entfernten Quellen registriert, oder
- auf ein **Cloud-/SSE**-Deployment verschoben wird, oder
- hinter einem gemeinsamen MCP-Gateway aggregiert wird (dann Tool-Allow-Listing
  und Poisoning-Erkennung auf Gateway-Ebene umsetzen).
