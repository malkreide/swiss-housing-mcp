# SessionStart-Hook: Klon-Aktualität

`session-start.sh` meldet beim Sessionstart, wie viele Commits der
ausgecheckte Stand hinter `origin/<Default-Branch>` liegt. Liegt er nicht
zurück, schweigt er.

## Warum

Ein veralteter Klon hat am 3.8.2026 **zweimal** eine rote CI erzeugt, deren
Ursache nicht im Diff stand — die fehlenden Commits waren jeweils genau die,
die das Gate einführten, an dem der Branch scheiterte. Wer nur den Diff
liest, sucht den Fehler in den falschen Dateien. Die Prüfung kostet eine
Sekunde und ersetzt diese Fehlersuche.

Das ist die Automatisierung des Abschnitts «Vor der Arbeit» in `CLAUDE.md`.

## Die oberste Regel: der Hook blockiert nie

Ein Hook, der bei Netzproblemen die Arbeit anhält, wird nach dem zweiten Mal
abgeschaltet und schützt danach gar nichts. Deshalb endet das Skript in
*jedem* Fall mit Exit 0 und ohne Ausgabe, wenn es nicht sicher etwas zu
melden hat:

| Fall | Verhalten |
|---|---|
| `git` nicht installiert | still durch |
| kein Git-Repo / kein Remote `origin` | still durch |
| kein Netz, DNS flattert, Remote antwortet nicht | still durch (Timeout) |
| Default-Branch nicht ermittelbar | still durch |
| Repo verlangt Credentials | still durch (kein Prompt möglich) |
| ungeborener HEAD (Repo ohne Commit) | still durch |
| detached HEAD | funktioniert, meldet regulär |
| 0 Commits hinter dem Default-Branch | still durch |

Bewusst **kein** `set -e` und **kein** `set -o pipefail`: jeder Fehlschlag
hier ist ein erwarteter Zustand, kein Abbruchgrund. Ein `trap ... EXIT` deckt
auch unerwartete Signale ab.

Gegen Aufhängen wirken drei Dinge:

1. `timeout -k 2 $TIMEOUT_SEC` auf jeden Netzaufruf (Default 5 s, zwei
   Aufrufe im Worst Case). Fehlt `timeout`, greifen ersatzweise git-eigene
   `http.lowSpeedLimit`/`http.lowSpeedTime`.
2. `GIT_TERMINAL_PROMPT=0`, `GIT_ASKPASS`, `SSH_ASKPASS`, `ssh -oBatchMode=yes`
   — ein Credential-Prompt wäre sonst genau der Hänger, den der Hook
   verhindern soll.
3. `"timeout": 20` in `settings.json` als äusserer Deckel.

## Der Default-Branch wird ermittelt, nicht angenommen

Drei Stufen, in dieser Reihenfolge:

1. `git symbolic-ref refs/remotes/origin/HEAD` — kostet kein Netz, ist aber
   oft ungesetzt (frische Klone von Claude Code on the web haben ihn
   regelmässig nicht; in diesem Repo ist er ungesetzt).
2. `git ls-remote --symref origin HEAD` — autoritativ, ein Roundtrip.
3. Sonst: still raus.

Stufe 3 fällt **nicht** auf `main` zurück. Drei Server im Portfolio heissen
ihren Default-Branch `master` (`openlex-mcp`, `swiss-courts-mcp`,
`swisstopo-mcp`); dort scheitert ein fest verdrahtetes `main` mit «couldn't
find remote ref main». Wer das für ein Netzproblem hält, arbeitet weiter auf
genau dem veralteten Klon, vor dem der Hook warnen soll — so ist ein Branch
schon einmal 15 Commits alt geworden. Ein geratener Branchname erzeugt
entweder einen Fehlalarm oder einen stillen Fetch des Remote-HEAD, der mit 0
endet und nichts geprüft hat.

## Stellschrauben

- `SWISS_HOUSING_HOOK_TIMEOUT` — Sekunden pro Netzaufruf (Default `5`).
- Der Hook läuft lokal **und** in Claude Code on the web. Er ist bewusst
  nicht auf `CLAUDE_CODE_REMOTE` eingegrenzt: der veraltete Klon ist gerade
  lokal der Normalfall.

## Manuell testen

```bash
.claude/hooks/session-start.sh            # echter Lauf
SWISS_HOUSING_HOOK_TIMEOUT=1 .claude/hooks/session-start.sh
```
