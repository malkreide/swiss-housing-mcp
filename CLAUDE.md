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

### Wenn Codex gar nicht erst hinsieht

Die Zeile oben unterstellt, dass es einen Befund geben *kann*. Das ist nicht
immer so, und man sieht es dem PR nicht an.

Am 21.8.2026 war das Code-Review-Kontingent zwischen 08:41 und 09:48
aufgebraucht — davor echte Reviews, danach in 30 Repos nur noch:

```
You have reached your Codex usage limits for code reviews.
```

Wie lange die Sperre dauerte, geben die Beobachtungen nur als Spanne her. Vier
Zeitpunkte sind belegt: letzter gelungener Review am 21.8. um 08:41, erste
Limit-Meldung um 09:48, letzte beobachtete Limit-Meldung am 22.8. um 11:03,
erste *andere* Meldung am 23.8. um 08:22.

Zwischen erster und letzter Limit-Meldung liegen **25 h 15 min**. Das ist der
Abstand zweier Fehlschläge, nicht die Dauer einer Sperre. Wer ihn Untergrenze
nennt, hat die durchgehende Erschöpfung schon vorausgesetzt, die er belegen
soll: Öffnete sich das Fenster zwischendurch und schloss es sich durch neue
Auslöser wieder, waren es zwei kurze Sperren und nie eine von 25 Stunden.
Untergrenze einer *einzelnen* Sperre sind die 25 h 15 min nur unter genau dieser
Annahme — und die ist unbelegt.

Nach oben trägt die Rechnung dagegen. Die längste mit den Beobachtungen
verträgliche Sperre reicht vom letzten Erfolg um 08:41 bis zur abweichenden
Meldung um 08:22, also **47 h 41 min**; länger kann keine einzelne gewesen sein.
Wer stattdessen ab der ersten Limit-Meldung rechnet, unterschlägt die 67
Minuten, in denen das Kontingent schon weg gewesen sein kann, und nennt die
Spanne zwischen zwei Beobachtungen eine Obergrenze.

Beobachtungspunkte sind keine Messreihe — die 21 Stunden vor der abweichenden
Meldung liefen ganz ohne Codex-Auslöser, dort hat niemand gemessen.

In der Zwischenzeit sind 32 PRs mit formal erfülltem Häkchen gemergt worden,
ohne dass jemand hineingesehen hat, und am 22.8. noch einmal 43.

**Fünf** Gründe, warum unter einem PR kein Befund steht. Harmlos sind zwei —
und der zweite davon, der letzte in der Liste, sieht aus wie ein Ausfall:

- **Kein Befund** — dann schreibt er einen gewöhnlichen Issue-Kommentar:

  ```
  Codex Review: Didn't find any major issues. Swish!
  ```

  Der Schlusssatz wechselt bei jedem Lauf («Delightful!», «Keep it up!»,
  «More of your lovely PRs please.»); stabil ist nur der Satz davor. Der
  Infokasten, den Codex unter jeden Review setzt, behauptet eine Reaktion, und
  sein Wortlaut hat sich geändert — am 23.8. «otherwise it will react with 👍»,
  am 29.8. ausführlicher: «reacts with 👀 while any review is running, comments
  if it has suggestions, and reacts with 👍 once all reviews finish with no
  findings». Am 23.8. kam in sechs Repos die Meldung und in keinem die
  Reaktion; am 29.8. kam die Reaktion und keine Meldung. Der Kasten trifft
  damit weder das eine noch das andere zuverlässig — er ist keine Quelle, auch
  nicht in seiner neuen Fassung.
- **Der PR ist ein Draft** — darauf läuft Codex nicht an.
- **Das Kontingent ist weg** — dann schreibt er die Meldung oben.
- **Für das Repo fehlt eine Environment** — dann schreibt er:

  ```
  To use Codex here, create an environment for this repo.
  ```
- **Der Lauf geht durch, aber das Urteil steht nicht dort, wo man es sucht** —
  dann steht unter dem PR eine Statustabelle, die sich selbst fortschreibt:

  ```
  ## Codex Review Summary

  | Review | Status | Commit | Review trigger |
  | 📝 Code Review | ✅ Completed 2026-08-29T08:53:40Z | 5a3e61e | Draft marked ready |
  ```

  Am 29.8. in diesem Repo, PR #41: Die Statuszeile stand um 08:52:22 auf
  `🔄 Running` und um 08:53:40 auf `✅ Completed` — ein Lauf von 78 Sekunden,
  vollständig durchgezogen. Dazu gibt es **kein** Review-Objekt und **keine**
  Befundlos-Meldung: `get_reviews` bleibt leer, `get_comments` liefert genau
  diesen einen Kommentar, und der Kommentar selbst trägt keine Reaktion. Der
  **PR** trägt dagegen eine 👍 (`reactions.total_count: 1`) — die Reaktion sitzt
  also am PR, nicht am Kommentar, und wer nur den Kommentar abfragt, sieht sie
  nicht.

Der vierte kam erst zum Vorschein, als der dritte wegfiel, und das ist kein
Zufall: Die Prüfungen liegen hintereinander. Dass es diese Reihenfolge ist und
nicht die umgekehrte, lässt sich an einem einzigen Repo ablesen — in
`swiss-public-data-mcp` bekam PR #54 am 22.8. um 10:56:55 die Kontingent-Meldung
und PR #56 am 23.8. um 08:22:20 die Environment-Meldung. Läge die
Environment-Prüfung vorn, hätte #54 sie schon am Vortag gesehen; die Environment
fehlte ja bereits. Zwei Meldungen aus demselben Repo schlagen hier jede
Vermutung über die Reihenfolge.

Der fünfte steht nicht in dieser Kette, sondern dahinter: Bei ihm sind alle
vier Prüfungen durch, Codex läuft an und kommt bis ans Ende. Nur trägt das
Ergebnis keine der beiden Formen, an denen dieser Abschnitt es zu erkennen
gelernt hat — kein Review-Objekt, keine Befundlos-Meldung.

Getragen hat es beide Male die 👍 am PR — #41 und #42 tragen je eine, und
beide Kommentare keine. Das ist die Umkehrung des 23.8.: Damals kam in sechs
Repos die Befundlos-Meldung und in keinem die Reaktion, hier kommt zweimal die
Reaktion und keine Meldung. Die beiden Träger vertreten einander also nicht
verlässlich; wer nur einen davon abfragt, zählt je nach Tag Geprüftes als
ungeprüft oder umgekehrt.

Zwei Vorbehalte, beide unerledigt. Erstens ist **nicht belegt, dass die 👍 von
Codex stammt** — `reactions` liefert nur die Zahl, nicht den Urheber; das klärt
erst eine Abfrage, die die Reagierenden auflistet. Zweitens liefen beide Reviews
vollständig nach dem Merge. Ob Codex auf einem geschlossenen PR einen Befund
noch absetzen würde, ist damit nicht geprüft — keiner der beiden Läufe hatte
offenbar einen. Zwei befundlose Läufe belegen zwei befundlose Läufe, nicht die
Fähigkeit, einen Befund abzusetzen. Ein Befund auf einem bereits gemergten PR
bleibt der ungetestete Fall.

Bis dahin gilt: Eine `Completed`-Zeile belegt, dass ein Lauf stattfand — nicht,
dass er nichts gefunden hat. Wer sie als Freigabe liest, hat die Frage, die
dieser Abschnitt stellt, mit dem Beleg beantwortet, dass überhaupt jemand
hingesehen hat.

Praktisch heisst das: **Eine verschwundene Limit-Meldung ist keine Entwarnung.**
Sie kann bedeuten, dass das Kontingent wieder da ist — und dass jetzt etwas
anderes den Review verhindert. Belegt ist eine Prüfung erst durch ein
Review-Objekt **oder** eine Befundlos-Meldung; eine `Completed`-Zeile belegt
den Lauf, aber nicht sein Urteil. Wer nur das Objekt gelten lässt,
zählt jeden befundlosen Review als ungeprüft — und baut sich denselben Fehlalarm
ein, den dieser Abschnitt verhindern soll, nur in die andere Richtung.

«Kein Kommentar» heisst also nicht «geprüft und sauber». Unterscheiden lässt es
sich an der Form: Ein Review **mit** Befund ist ein Review-Objekt
(«💡 Codex Review», mit Commit-Angabe); ein Review **ohne** Befund und die
beiden Ausfallmeldungen — Kontingent wie Environment — sind gewöhnliche
Issue-Kommentare und trennen sich nur im Text. Beim Draft gibt es überhaupt
nichts, weil Codex nicht anläuft; ein kommentarloser Draft ist deshalb kein
Beleg, sondern ein nicht durchgeführter Test.

Die Statustabelle ist ebenfalls ein gewöhnlicher Issue-Kommentar, unterscheidet
sich von den dreien aber in einem Punkt, der beim Nachsehen zählt: Sie wird
**in place fortgeschrieben**. Derselbe Kommentar trug um 08:52:23 `Running` und
um 08:53:44 `Completed`; `created_at` bleibt dabei stehen, nur `updated_at`
wandert. Wer einmal hinsieht, liest einen Zwischenstand und hält ihn für das
Ergebnis — genau so ist hier zuerst «der Review hat nicht stattgefunden»
herausgekommen, obwohl er 78 Sekunden später fertig war. Also `updated_at`
mitlesen und bei `Running` erneut abfragen, statt den ersten Blick zu buchen.

Das sind verschiedene Abfragen — `get_reviews` fürs Objekt, `get_comments` für
die Kommentare, und für die Reaktion am PR eine dritte (`issue_read`/`get` auf
dieselbe Nummer, Feld `reactions`); wer nur eine nimmt, übersieht den Rest.
Genau so ist die Limit-Meldung zuerst durchgerutscht, und genau so wäre am
29.8. die 👍 durchgerutscht: Der Kommentar trug keine, der PR schon.

Der Kommentarzähler allein reicht ohnehin nicht: `comments: 1` kann die
Befundlos-, die Kontingent-, die Environment-Meldung **oder** eine Statustabelle
sein — vier gegensätzliche Bedeutungen unter derselben Zahl, und die letzte
wechselt ihre Bedeutung sogar, ohne dass die Zahl sich rührt. Den Text lesen,
nicht die Zahl. Und einen unbekannten Text wörtlich zitieren, statt ihn in eine
der bekannten Schubladen zu zwingen: Dieser Abschnitt musste erst von drei auf
vier und dann auf fünf Gründe wachsen, und die 👍-Reaktion stand hier zwei
Fassungen lang als Tatsache.

Und ein befundloser Lauf ist kein Freispruch. Am 23.8. lief derselbe Text durch
42 Reviews: 36 meldeten denselben P2-Befund, 6 die Befundlos-Meldung — gleiche
Eingabe, gegenteiliges Urteil, alles in denselben neun Minuten. Ein sauberer
Lauf sagt damit etwas über den Lauf, nicht über den Text. Wer sein Häkchen
daran hängt, hängt es an einen Münzwurf.

Portfolio-weit nachsehen:

```
search_pull_requests: user:malkreide commenter:chatgpt-codex-connector[bot] updated:>=<Datum>
```

Findet nur, wo er *kommentiert* hat. Repos ohne PR-Aktivität tauchen nicht auf
— das ist kein Beleg, dass dort geprüft wurde.

Zweiter Weg, den Prüfer zu verlieren, ganz ohne Kontingentproblem: zu schnell
mergen. Am 21./22.8. lagen zwischen «ready for review» und Merge mehrfach drei
bis fünf Sekunden. Codex wird beim Umschalten von Draft auf ready ausgelöst und
braucht danach Zeit; wer sofort mergt, hat das Häkchen gesetzt und den Review
nicht abgewartet.

Wie viel Zeit, ist am 29.8. zweimal gemessen: **78 und 62 Sekunden** von
`Running` bis `Completed` — PR #41 dieses Repos 08:52:22 → 08:53:40, PR #42
09:00:08 → 09:01:09. Zwei Messungen sind keine Verteilung; wer wartet, sollte
mit gut einer Minute rechnen und nicht mit Sekunden, und die 78 nicht für eine
Obergrenze halten.

Beide Male lag der Merge davor — `closed_at` 08:52:19 und 09:00:06 —, der Lauf
begann also zwei bis drei Sekunden nach dem Merge und lief vollständig auf
einem geschlossenen PR. Abgebrochen wurde er dabei nicht: Der Merge nimmt einem
nicht den Lauf, sondern nur die Gelegenheit, sein Ergebnis vor dem Merge zu
sehen und darauf zu reagieren.

Das Kontingent hängt am Konto, nicht am Repo, und Code-Reviews haben einen
eigenen Topf — nur GitHub-getriggerte Reviews zählen hinein. ChatGPT-Pläne
fahren ein rollendes Fünf-Stunden-Fenster plus Wochenlimits; welches greift,
steht im Codex-Dashboard. Welches hier griff, ist **offen**. Die Lücke oben
schliesst das Fünf-Stunden-Fenster nicht aus: Es kann sich zwischendurch
geöffnet und durch neue Auslöser wieder erschöpft haben. Das auszuschliessen
bräuchte den Nachweis, dass in der ganzen Spanne kein einziger Review durchlief
— den gibt es nicht, weil nur Fehlschläge beobachtet wurden. Eine lange Reihe
von Fehlschlägen belegt eine lange Reihe von Fehlschlägen, nicht ihre Ursache.

Zeigt das Dashboard freies Kontingent, während Reviews weiter scheitern, ist
das ein bekannter Fehler bei mehreren verbundenen Konten — dann den
GitHub-Connector in den Codex-Einstellungen trennen und neu verbinden.

Die Environment legt man unter `chatgpt.com/codex/cloud/settings/environments`
an, und zwar **je Repo**. Die Meldung sagt es selbst («for this repo»), und am
23.8. war es genau so: In `swiss-public-data-mcp` fehlte sie, dort kam kein
Review; in den übrigen Repos lief Codex am selben Morgen durch. Eine
Environment fürs Konto genügt also nicht — wer eine anlegt und den Rest für
erledigt hält, mergt weiter Ungeprüftes.

### Wenn zwei Agenten dasselbe tun

Vor dem Anlegen eines Branches mit vorgegebenem Namen prüfen, ob es ihn schon
gibt:

```bash
git ls-remote --heads origin claude/<name> | wc -l
```

Steht dort `1`, arbeitet jemand anderes daran — mit Schreibrecht auf denselben
Ref.

Ein PR mit leerem Diff wird geschlossen, nicht gemergt. Der Test ist
`get_files` auf dem PR: kommt `[]` zurück, ändert er nichts. Ein grüner Check
sagt dazu nichts — die CI prüft den Head, nicht die Differenz zur Basis.

Am 21.8.2026 liefen zwei Sessions dieselbe Aufgabe über 45 Repos, auf den
Branches `claude/codex-review-audit-templates-9sn6mx` und
`claude/codex-review-audit-7ioh56`. Wo die eine zuerst nach `main` kam, wurde
`main` in den Branch der anderen gemergt und der add/add-Konflikt zugunsten
von `main` aufgelöst. Übrig blieben 14 PRs, die durch sämtliche Gates grün
liefen und nichts enthielten; sie wurden gemergt und hinterliessen leere
Merge-Commits. Mit den zwei Folge-PRs, die aus demselben Grund gegenstandslos
waren, waren 16 der 59 PRs jenes Tages reine Reibung.

Dieselbe Klasse wie der handgeschriebene Stub, der denselben Feldnamen annahm
wie der Code: Nichts ist rot, weil nichts geprüft wird, worauf es ankommt.

## Teil 2 — dieses Repo

**ruff:** genau eine Quelle — `ruff==0.16.3` im `[dev]`-Extra von
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
python scripts/check_version_sync.py
python scripts/check_ruff_pin.py
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
```

Der Block setzt `pip install -e ".[dev]"` voraus; die CI setzt für Import-,
Unit- und Live-Schritt zusätzlich `PYTHONPATH=src`.

**Die ruff-Gates decken `scripts/` mit** — bis zum Commit «ci: `scripts/` in
den ruff-Scope nehmen» nicht, und von den inzwischen vier Dateien dort sind
zwei selbst CI-Gates (`check_version_sync.py`, `check_ruff_pin.py`). Kein
`include` unter `[tool.ruff]` setzen: der Umfang der genannten Pfade stimmt
(nachgemessen, eine Sonde in `tests/` lässt beide Gates fallen).

Der erste Lauf mit dem erweiterten Umfang war hier **grün** — die damals
drei Dateien bestanden ruff schon vorher. Das ist kein Argument gegen die
Erweiterung, sondern der Grund, warum die Lücke so lange offenblieb: sie biss
noch nicht.

**Die zwei Jobs sind ungleich breit.** `test` (Syntax, Import, pytest,
Versions-Sync) fährt die Matrix 3.11/3.12/3.13, `lint` (die zwei ruff-Gates)
läuft ohne Matrix auf 3.11. Ein grünes 3.12/3.13 sagt über ruff nichts aus.
`test` setzt kein `fail-fast: false`.

**Live-Tests:** eigener Job in `ci.yml`, nächtlich per Cron (`29 3 * * *`),
auf PRs per `if:` übersprungen. Der Lauf wird eingeordnet statt am Exit-Code
gemessen; ein Befund öffnet oder schliesst ein Issue. DRIFT-005 ist erfüllt.
