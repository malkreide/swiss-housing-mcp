#!/usr/bin/env bash
# `labels:` aus .github/dependabot.yml entfernen — portfolioweit, je ein Pull Request.
#
# WARUM
# `labels:` wegzulassen ist die STAERKERE Konfiguration, nicht die schwaechere.
# Die Optionsreferenz von Dependabot sagt: ohne den Schluessel bekommt jeder PR
# ein `dependencies`-Label, bei mehreren Paketmanagern zusaetzlich eines fuers
# Oekosystem — «Dependabot creates these default labels automatically, as
# necessary in your repository». Eine eigene Liste ersetzt diesen Vorgabesatz,
# und «if any of these labels is not defined in the repository, it is ignored»:
# Dependabot haengt dann nur einen Kommentar an jeden PR und laesst ihn
# ungelabelt — kein roter Check, kein Log.
#
# Die Zeile war also nicht bloss wirkungslos, sie war schaedlich: Sie hat einen
# Vorgabesatz, der sich selbst anlegt und pflegt, durch Namen ersetzt, die das
# Repo grossenteils nicht kannte.
#
# Der erste Anlauf hatte das falsch herum begruendet («Dependabot legt Labels
# nicht an»). Am 29.8.2026 zeigte eine Messung in zehn Repos, dass `dependencies`
# in sieben davon sehr wohl existiert — mit GitHubs Standardbeschreibung, also
# von Dependabot selbst angelegt. Das las sich zuerst wie ein Widerspruch zur
# Aktion und war in Wahrheit ihr bester Beleg. Erst die Spec nachlesen, dann
# einordnen.
#
# Ein Gate dagegen kann es trotzdem nicht geben: Labels sind GitHub-Zustand,
# kein Dateiinhalt.
#
# DIE REPO-LISTE WIRD ABGEFRAGT, NICHT GEPFLEGT
# Die Vorgaengerfassung trug 23 Namen fest verdrahtet. Am 29.8.2026 hatte das
# Konto 43 aktive `*-mcp`-Server — die Liste deckte also knapp die Haelfte ab,
# und man sah es ihr nicht an: Ein Repo, das nicht in der Liste steht, wird
# nicht uebersprungen, es kommt gar nicht erst vor. Deshalb fragt das Skript
# `gh repo list` und filtert; ausgenommen wird nur, was unten mit Begruendung
# unter AUSNAHMEN steht.
#
# VORAUSSETZUNGEN
#   - eine Bash. Unter Windows heisst das Git Bash, nicht PowerShell: dort ist
#     `./labels_entfernen.sh` kein Befehl, sondern ein Dateiname. Man muss die
#     Konsole aber nicht wechseln, `bash` ist aus PowerShell aufrufbar:
#
#         & 'C:\Program Files\Git\bin\bash.exe' ./labels_entfernen.sh --dry-run
#
#     Den vollen Pfad nehmen, nicht bloss `bash`. Unter Windows liegt in
#     `C:\Windows\System32\bash.exe` der WSL-Starter, und der bringt eine
#     eigene Umgebung mit — ohne den `gh`-Login und ohne das Python, die auf
#     der Windows-Seite eingerichtet sind.
#
#     Diese Datei muss dafuer LF-Zeilenenden haben; `.gitattributes` im
#     Repo-Wurzelverzeichnis sorgt dafuer. Mit CRLF steigt bash schon in
#     Zeile 1 aus.
#   - `gh` angemeldet mit Schreibrecht auf die Repos
#   - `entferne_dependabot_labels.py` im selben Verzeichnis wie dieses Skript
#   - Python 3 mit `pyyaml` (das Entfernen-Skript verweigert ohne die
#     Gegenprobe den Dienst — siehe dort). Wie der Interpreter heisst, sucht
#     das Skript selbst heraus; siehe PY weiter unten.
#
# VERWENDUNG
#   ./labels_entfernen.sh --dry-run                 # nur zeigen
#   ./labels_entfernen.sh --repos "a-mcp b-mcp"     # nur diese, statt Abfrage
#   ./labels_entfernen.sh                           # Branches, Commits, PRs
#
# Das Skript ist wiederholbar: Repos, in denen der Branch schon existiert oder
# nichts mehr zu entfernen ist, werden uebersprungen statt doppelt bearbeitet.
set -uo pipefail

HIER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENTFERNER="$HIER/entferne_dependabot_labels.py"
BRANCH="claude/dependabot-labels-entfernen"
OWNER="malkreide"

# `register-mcp`: dort existieren die vier Labels seit dem 28.8.2026, die
# Zeile kostet nichts mehr.
#
# `openlex-mcp`: dort steht ein eigenes Gate, `tests/test_dependabot_labels.py`,
# das verlangt, dass die Konfiguration genau `dependencies` deklariert. Der Lauf
# vom 29.8.2026 hat dort einen roten PR erzeugt (#75, geschlossen). Ob das Gate
# bleiben soll, ist eine Entscheidung fuer jenes Repo — nach der Optionsreferenz
# zementiert es einen engeren Zustand als die Vorgabe. Bis das dort geklaert ist,
# bleibt das Repo aussen vor, damit der naechste Lauf denselben roten PR nicht
# erneut anlegt.
AUSNAHMEN=(register-mcp openlex-mcp)

DRY=""
REPO_VORGABE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1; shift ;;
    --repos)   REPO_VORGABE="${2:-}"; shift 2 ;;
    *)
      # Unbekanntes Argument ist ein Abbruch, keine Fussnote. Die
      # Vorgaengerfassung pruefte nur `[ "$1" = "--dry-run" ]` — ein
      # `--dryrun` fiel damit stillschweigend in den scharfen Lauf und legte
      # in jedem Repo einen PR an.
      echo "FEHLER: unbekanntes Argument: $1" >&2
      echo "Erlaubt: --dry-run, --repos \"a b c\"" >&2
      exit 2 ;;
  esac
done

[ -f "$ENTFERNER" ] || { echo "FEHLER: $ENTFERNER fehlt" >&2; exit 2; }
command -v gh >/dev/null || { echo "FEHLER: gh nicht gefunden" >&2; exit 2; }
# Python-Interpreter bestimmen, statt `python3` fest zu verdrahten. Unter Git
# Bash auf Windows gibt es `python3` nicht zwingend — dort heisst die Datei oft
# nur `python.exe`, und das Skript waere mit «command not found» ausgestiegen,
# obwohl ein taugliches Python da ist. Umgekehrt ist `python` auf manchen
# Systemen noch Python 2 und auf Windows ohne Installation ein Store-Stub, der
# bloss eine Werbeseite oeffnet. Deshalb wird jeder Kandidat zusaetzlich
# gefragt, ob er wirklich Python 3 ist.
PY=""
for KANDIDAT in python3 python py; do
  command -v "$KANDIDAT" >/dev/null 2>&1 || continue
  "$KANDIDAT" -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' >/dev/null 2>&1 || continue
  PY="$KANDIDAT"; break
done
[ -n "$PY" ] || {
  echo "FEHLER: kein Python 3 gefunden (gesucht: python3, python, py)" >&2
  exit 2; }

"$PY" -c "import yaml" 2>/dev/null || {
  echo "FEHLER: $PY findet kein pyyaml — die Gegenprobe im Entferner laeuft" >&2
  echo "        dann nicht. Installieren in genau diesen Interpreter:" >&2
  echo "            $PY -m pip install pyyaml" >&2
  exit 2; }

ARBEIT="$(mktemp -d)"
trap 'rm -rf "$ARBEIT"' EXIT

# --- Repo-Liste ------------------------------------------------------------
if [ -n "$REPO_VORGABE" ]; then
  read -r -a REPOS <<< "$REPO_VORGABE"
else
  # Regel statt Aufzaehlung: aktive, eigene Repos, deren Name auf `-mcp`
  # endet. Das trifft die Server und laesst die Skill-Repos
  # (`mcp-audit-skill`, `mcp-continuous-auditor`, `awesome-mcp-servers`)
  # draussen, weil deren Namen anders gebaut sind.
  mapfile -t GEFUNDEN < <(
    gh repo list "$OWNER" --limit 300 --no-archived --source \
      --json name --jq '.[].name | select(endswith("-mcp"))' | sort
  )
  if [ "${#GEFUNDEN[@]}" -eq 0 ]; then
    echo "FEHLER: gh repo list lieferte nichts — Abbruch statt leerem Lauf" >&2
    exit 2
  fi
  REPOS=()
  for R in "${GEFUNDEN[@]}"; do
    haut_raus=""
    for A in "${AUSNAHMEN[@]}"; do [ "$R" = "$A" ] && haut_raus=1; done
    [ -n "$haut_raus" ] || REPOS+=("$R")
  done
fi

echo "Repos: ${#REPOS[@]}"
printf '  %s\n' "${REPOS[@]}"
echo

if [ -z "$DRY" ]; then
  # Ein scharfer Lauf legt in jedem Repo einen Branch und einen PR an. Das
  # einmal bestaetigen zu lassen kostet eine Zeile und faengt den Fall ab,
  # in dem die Liste anders aussieht als erwartet.
  read -r -p "Scharfer Lauf ueber ${#REPOS[@]} Repos. Weiter? [tippen: ja] " ANTWORT
  [ "$ANTWORT" = "ja" ] || { echo "abgebrochen"; exit 0; }
fi

TITEL="ci(dependabot): labels entfernen, die kein Repo anlegt"
read -r -d '' RUMPF <<'PRTEXT'
## Was ändert sich

Die `labels:`-Zeilen fallen aus `.github/dependabot.yml`.

## Warum

**Ohne `labels:` beschriftet Dependabot besser, nicht schlechter.** Die
[Optionsreferenz](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference)
sagt zum Vorgabeverhalten:

> All pull requests have a `dependencies` label. If you define more than one
> package manager, an additional label for the ecosystem or language is added
> to each pull request. […] Dependabot creates these default labels
> automatically, as necessary in your repository.

Und zu einer eigenen Liste:

> If any of these labels is not defined in the repository, it is ignored.

Eine eigene Liste **ersetzt** also den Vorgabesatz. Namen, die das Repo nicht
kennt, fallen weg; Dependabot hängt dafür nur einen Kommentar an jeden Pull
Request und lässt ihn ungelabelt:

```
The following labels could not be found: `dependencies`, `python`.
```

Kein roter Check, kein Log — nur diese Zeile. Am 28.8.2026 fehlten die
konfigurierten Labels in 23 von 24 geprüften Repos des Portfolios.

Die Zeile war damit nicht bloss wirkungslos, sondern schädlich: Sie hat einen
Vorgabesatz, der sich selbst anlegt und pflegt, durch grösstenteils
nicht existierende Namen ersetzt. Sie zu entfernen stellt die Vorgabe wieder
her — `dependencies` plus Ökosystem-Label, von Dependabot selbst angelegt.

`register-mcp` und `openlex-mcp` behalten ihre Zeile: dort existieren die
Labels, und `openlex-mcp` hat zusätzlich ein Gate, das sie verlangt.

## Prüfung

Der Schnitt ist semantisch gegengeprüft: Das Ergebnis parst, es führt kein
`labels` mehr, und die Struktur ist ansonsten identisch zur Ausgangsdatei.

---
_Generated by [Claude Code](https://claude.ai/code)_
PRTEXT
# `read -d ''` endet an EOF und nicht am Trenner, gibt also 1 zurueck. Ohne
# `set -e` ist das folgenlos; die Zeile steht hier, damit niemand spaeter
# `set -e` ergaenzt und sich wundert, warum das Skript hier aussteigt.

erledigt=0; uebersprungen=0; fehler=0

for R in "${REPOS[@]}"; do
  printf '\n=== %s ===\n' "$R"
  ZIEL="$ARBEIT/$R"
  URL="https://github.com/$OWNER/$R.git"

  # Erst fragen, dann klonen. Der Branch-Test kostet einen Bruchteil eines
  # Klons, und ein `ls-remote`, das nicht antwortet, darf nicht als «Branch
  # ist frei» durchgehen — deshalb der Exit-Code und nicht nur `wc -l`.
  if ! VORHANDEN="$(git ls-remote --heads "$URL" "$BRANCH" 2>/dev/null)"; then
    echo "  FEHLER: ls-remote fehlgeschlagen (Repo erreichbar?)"; fehler=$((fehler+1)); continue
  fi
  if [ -n "$VORHANDEN" ]; then
    echo "  uebersprungen: Branch $BRANCH existiert bereits remote"
    uebersprungen=$((uebersprungen+1)); continue
  fi

  if ! git clone --depth 1 -q "$URL" "$ZIEL" 2>/dev/null; then
    echo "  FEHLER: Klon fehlgeschlagen"; fehler=$((fehler+1)); continue
  fi

  # Standard-Branch ermitteln, nicht `main` annehmen: openlex-mcp,
  # swiss-courts-mcp und swisstopo-mcp heissen ihn `master`. Der Klon steht
  # ohnehin schon darauf.
  BASIS="$(git -C "$ZIEL" rev-parse --abbrev-ref HEAD)"
  if [ -z "$BASIS" ] || [ "$BASIS" = "HEAD" ]; then
    echo "  FEHLER: Standard-Branch nicht ermittelbar"; fehler=$((fehler+1)); continue
  fi

  DATEI="$ZIEL/.github/dependabot.yml"
  [ -f "$DATEI" ] || { echo "  uebersprungen: keine dependabot.yml"; uebersprungen=$((uebersprungen+1)); continue; }

  "$PY" "$ENTFERNER" "$DATEI"
  case $? in
    0) : ;;
    1) echo "  uebersprungen: kein \`labels:\` vorhanden"; uebersprungen=$((uebersprungen+1)); continue ;;
    *) echo "  FEHLER: Entferner meldet ein Problem (siehe oben) — Repo unangetastet"
       fehler=$((fehler+1)); continue ;;
  esac

  if [ -n "$DRY" ]; then
    echo "  --- Diff (dry-run, nur im Wegwerf-Klon) ---"
    git -C "$ZIEL" --no-pager diff -- .github/dependabot.yml | sed 's/^/  /'
    erledigt=$((erledigt+1)); continue
  fi

  git -C "$ZIEL" checkout -q -b "$BRANCH"
  git -C "$ZIEL" add .github/dependabot.yml
  git -C "$ZIEL" commit -q -m "$TITEL" -m \
"Ohne \`labels:\` beschriftet Dependabot besser, nicht schlechter. Die
Optionsreferenz sagt: jeder PR bekommt per Vorgabe ein \`dependencies\`-Label,
bei mehreren Paketmanagern zusaetzlich eines fuers Oekosystem, und Dependabot
legt diese Labels bei Bedarf selbst an. Eine eigene Liste ersetzt den
Vorgabesatz, und Namen, die das Repo nicht kennt, werden ignoriert — quittiert
mit einem Kommentar an jedem PR, ohne roten Check und ohne Log. Am 28.8.2026
fehlten die konfigurierten Labels in 23 von 24 geprueften Repos.

Die Zeile war damit nicht wirkungslos, sondern schaedlich: Sie hat einen
Vorgabesatz, der sich selbst pflegt, durch grossenteils nicht existierende
Namen ersetzt.

Der Schnitt ist semantisch gegengeprueft: Ergebnis parst, kein \`labels\` mehr,
Struktur sonst identisch.

\`register-mcp\` und \`openlex-mcp\` behalten ihre Zeile."

  if ! git -C "$ZIEL" push -q -u origin "$BRANCH"; then
    echo "  FEHLER: Push fehlgeschlagen"; fehler=$((fehler+1)); continue
  fi
  # stderr NICHT verwerfen: die Vorgaengerfassung meldete nur «PR nicht
  # angelegt» und verschwieg, warum.
  if gh pr create -R "$OWNER/$R" --base "$BASIS" --head "$BRANCH" \
       --title "$TITEL" --body "$RUMPF" --draft >/dev/null; then
    echo "  PR angelegt (Basis: $BASIS, Draft)"
    erledigt=$((erledigt+1))
  else
    echo "  FEHLER: PR nicht angelegt (Branch ist gepusht)"; fehler=$((fehler+1))
  fi
done

printf '\n%s\n' "-----------------------------------------"
printf 'erledigt: %d   uebersprungen: %d   Fehler: %d\n' "$erledigt" "$uebersprungen" "$fehler"
if [ -n "$DRY" ]; then
  echo "(dry-run — nichts gepusht)"
elif [ "$erledigt" -gt 0 ]; then
  echo
  echo "Die PRs sind Drafts. Codex laeuft auf Drafts NICHT an — zum Pruefen"
  echo "erst auf «ready for review» stellen und den Review abwarten, nicht"
  echo "sofort mergen."
fi
