# CLAUDE.md

## Teil 1 — Konventionen (portfolio-weit)

### Vor der Arbeit

Klon-Aktualität prüfen — Standard-Branch ermitteln, nicht `main` annehmen:

```bash
B=$(git ls-remote --symref origin HEAD | sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p')
git fetch origin "${B:?Standard-Branch nicht ermittelbar}" &&
  git rev-list --count HEAD..FETCH_HEAD
```

Drei Server im Portfolio heissen ihren Standard-Branch `master`
(`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`); dort scheitert ein fest
verdrahtetes `origin/main` mit «couldn't find remote ref main». Wer das für ein
Netzproblem hält, arbeitet weiter auf genau dem veralteten Klon, vor dem dieser
Absatz warnt. Den `:?`-Schutz nicht weglassen: Bei leerem `B` fetcht git still
den Remote-HEAD und endet mit 0.

Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht.
Am 3.8.2026 zweimal passiert — beide Male fehlten genau die Commits, die
das Gate einführten, an dem der Branch scheiterte.

Gates lokal fahren, mit der GEPINNTEN ruff-Version aus der CI. Eine andere
Version meldet Abweichungen, die niemand verursacht hat.

### Tests

Gegenprobe ist Pflicht. Ein Test, der grün bleibt, wenn man die
Implementierung entfernt, prüft nichts. Jede neue Zusicherung einzeln
neutralisieren und zeigen, dass genau die zugehörigen Tests fallen.

Zwei Fallen, die beide grün blieben:

- Eine Fake-Uhr, die nur beim Schlafen vorrückt, kann eine Zusicherung über
  echte Zeit nicht widerlegen.
- `monkeypatch.setattr(modul.asyncio, "sleep", ...)` greift ins Modul
  `asyncio` selbst und entschärft die Mechanik im ganzen Prozess. Patche
  einen Modul-Alias (`_sleep = asyncio.sleep`), nicht das fremde Modul.

Handgeschriebene Fixtures kodieren die Annahme des Autors und können sie
nicht widerlegen. Mindestens eine aufgezeichnete Antwort pro externem
Endpunkt, mit Aufnahmedatum.

### Wenn etwas rot ist

Roter Live-Test: erst die Quelle abfragen, dann einordnen. Nicht aus der
Fehlermeldung schliessen. Am 3.8.2026 hiess "nicht gefunden" nicht, dass der
Datensatz weg war, sondern dass die Quelle die Schreibweise ihrer Kopfzeile
gewechselt hatte — vier von sechs Datensätzen produktiv kaputt, alle
Unit-Tests grün.

PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.

Ein Codex-Review auf einem PR wird beantwortet oder behoben, nie ignoriert.

## Teil 2 — dieses Repo

**ruff:** genau eine Quelle — `ruff==0.16.1` im `[dev]`-Extra von
`pyproject.toml`. Ein dev-Install reicht also, lokal wie in der CI. Keine
zweite Version in die Workflows schreiben: ein solcher Schritt läuft nach dem
Install und überstimmt den Pin still (`ci.yml` hatte einen;
`test_werkzeug_versionen.py` hält beides fest). Eine `.pre-commit-config.yaml`
gibt es nicht.

Vor dem Lauf `ruff --version` prüfen: ein älteres ruff früher im `PATH`
schlägt den Pin, ohne dass der Install etwas meldet.

**Gates, wörtlich aus der CI:**

```bash
python -m py_compile src/swiss_housing_mcp/server.py src/swiss_housing_mcp/gwr.py
python -c "from swiss_housing_mcp.server import mcp; print('Import OK')"
pytest -m "not live" -v
python scripts/check_ruff_pin.py
ruff check src/ tests/
ruff format --check src/ tests/
```

**Die ruff-Gates lassen `scripts/` aus** — anders als in den meisten
Schwester-Servern, wo `src/ tests/ scripts/` geprüft wird. Die zwei Dateien
dort sind damit ungeprüft; wer sie anfasst, bekommt kein Gate-Feedback. Kein
`include` unter `[tool.ruff]` setzen — der Umfang der genannten Pfade stimmt
(nachgemessen, eine Sonde in `tests/` lässt beide Gates fallen).

Heute bestehen die zwei Dateien ruff ohnehin — nachgemessen. Die Lücke ist
also real, beisst aber noch nicht; genau deshalb fällt sie beim nächsten
Anfassen niemandem auf.

**Fünf ist die ganze Liste — es gibt kein Versions-Sync-Gate.** `scripts/`
enthält nur `classify_live_run.py` und `record_fixtures.py`, ein
`check_version_sync.py` fehlt, und kein Workflow ruft eines auf.
`pyproject.toml` und `server.json` stehen beide auf `0.1.0`, gehalten wird
das von nichts. Die Schwester-Server fahren den Gate; beim Anheben hier also
beide Stellen von Hand.

**Die zwei Jobs sind ungleich breit.** `test` (Syntax, Import, pytest) fährt
die Matrix 3.11/3.12/3.13, `lint` (die zwei ruff-Gates) läuft ohne Matrix auf
3.11. Ein grünes 3.12/3.13 sagt über ruff nichts aus. `test` setzt kein
`fail-fast: false`.

**Live-Tests:** eigener Job in `ci.yml`, nächtlich per Cron (`29 3 * * *`),
auf PRs per `if:` übersprungen. Der Lauf wird eingeordnet statt am Exit-Code
gemessen; ein Befund öffnet oder schliesst ein Issue. DRIFT-005 ist erfüllt.
