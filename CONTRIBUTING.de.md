# Beitragen zu swiss-housing-mcp

[🇬🇧 English Version](CONTRIBUTING.md)

Vielen Dank für Ihr Interesse an einem Beitrag zu `swiss-housing-mcp`! Dieses Projekt ist Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide).

---

## Möglichkeiten zum Mitwirken

### Fehler melden

Eröffnen Sie ein [GitHub-Issue](https://github.com/malkreide/swiss-housing-mcp/issues) und geben Sie an:

- Eine klare Beschreibung des Problems
- Schritte zur Reproduktion (idealerweise mit der betroffenen EGID/EWID oder Adresse)
- Erwartetes vs. tatsächliches Verhalten
- Python-Version und Betriebssystem

### Einen neuen Kantons-Dump oder eine Datenquelle vorschlagen

Die GWR/RegBL-Dumps werden pro Kanton publiziert. Wenn Sie einen Kanton oder Datensatz finden, der unterstützt werden sollte:

1. Eröffnen Sie ein Issue mit dem Titel `[Data] <Kanton/Datensatz>: <kurze Beschreibung>`
2. Geben Sie eine Beispiel-Quell-URL und eine Beschreibung der enthaltenen Daten an
3. Verifizieren Sie die Quelle idealerweise vor dem Einreichen gegen die Live-Quelle

### Dokumentation verbessern

Tippfehler, unklare Erklärungen oder fehlende Beispiele sind als Pull Requests immer willkommen — kein Issue nötig.

### Code beitragen

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch: `git checkout -b feat/mein-feature`
3. Halten Sie sich an den Code-Stil (Ruff für Linting/Formatierung)
4. Ergänzen oder aktualisieren Sie Tests in `tests/`
5. Führen Sie die Test-Suite vor dem Einreichen aus: `PYTHONPATH=src pytest tests/ -m "not live"`
6. Reichen Sie einen Pull Request mit einer klaren Beschreibung Ihrer Änderungen ein

---

## Entwicklungs-Setup

```bash
git clone https://github.com/malkreide/swiss-housing-mcp.git
cd swiss-housing-mcp
pip install -e ".[dev]"
```

**Tests ausführen:**

```bash
# Unit-Tests (keine Netzwerkverbindung erforderlich, respx-gemockt)
PYTHONPATH=src pytest tests/ -m "not live"

# Integrationstests (Live-Upstream)
PYTHONPATH=src pytest tests/ -m "live"
```

**Linten und formatieren:**

```bash
ruff check src/ tests/
ruff format src/ tests/
```

---

## Commit-Konvention

Dieses Projekt verwendet [Conventional Commits](https://www.conventionalcommits.org/):

| Präfix | Verwendung |
|---|---|
| `feat:` | Neues Tool oder neue Datenquelle |
| `fix:` | Fehlerbehebung |
| `docs:` | Nur Dokumentation |
| `test:` | Tests hinzufügen oder aktualisieren |
| `refactor:` | Code-Umstrukturierung ohne Verhaltensänderung |
| `chore:` | Build, Abhängigkeiten, CI |

---

## Verhaltenskodex

Seien Sie respektvoll und konstruktiv. Dies ist ein kleines Open-Source-Projekt, das in der Freizeit gepflegt wird — Geduld wird geschätzt.

---

## Lizenz

Mit Ihrem Beitrag erklären Sie sich damit einverstanden, dass Ihre Beiträge unter der [MIT-Lizenz](LICENSE) lizenziert werden.
