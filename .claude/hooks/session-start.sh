#!/usr/bin/env bash
#
# SessionStart-Hook: meldet, wie viele Commits der ausgecheckte Stand hinter
# origin/<Default-Branch> liegt. Schweigt, wenn nichts fehlt.
#
# WARUM (siehe auch .claude/hooks/README.md):
# Ein veralteter Klon hat am 3.8.2026 zweimal eine rote CI erzeugt, deren
# Ursache nicht im Diff stand — die fehlenden Commits waren jeweils genau die,
# die das Gate einfuehrten, an dem der Branch scheiterte. Die Pruefung kostet
# eine Sekunde und ersetzt eine Fehlersuche in den falschen Dateien.
#
# OBERSTE REGEL: Dieser Hook blockiert die Session NIEMALS.
# Kein Netz, kein Remote, detached HEAD, flatterndes DNS, fehlendes git,
# Credential-Prompt — jeder Fall geht still durch (Exit 0, keine Ausgabe).
# Ein Hook, der bei Netzproblemen die Arbeit anhaelt, wird nach dem zweiten
# Mal abgeschaltet und schuetzt danach gar nichts.

# Bewusst KEIN `set -e` und KEIN `set -o pipefail`: jeder Fehlschlag hier ist
# ein erwarteter Zustand, kein Abbruchgrund. `set -u` waere ebenfalls riskant,
# weil ein nicht gesetztes Env den Hook killen wuerde.

# Unter allen Umstaenden mit 0 enden, auch bei einem unerwarteten Signal.
trap 'exit 0' EXIT HUP INT TERM

# Sekunden pro Netzaufruf. Worst case zwei Aufrufe = 2x dieser Wert.
TIMEOUT_SEC="${SWISS_HOUSING_HOOK_TIMEOUT:-5}"

# Nichts darf interaktiv nachfragen — ein Credential-Prompt wuerde den
# Sessionstart aufhaengen, also genau das, was dieser Hook verhindern soll.
export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS=/bin/true
export SSH_ASKPASS=/bin/true
export SSH_ASKPASS_REQUIRE=never
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -oBatchMode=yes -oStrictHostKeyChecking=accept-new}"

command -v git >/dev/null 2>&1 || exit 0

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
git remote get-url origin >/dev/null 2>&1 || exit 0

# `timeout` fehlt auf manchen Minimal-Images; dann ohne Deckel laufen, aber
# git bekommt eigene Abbruchkriterien mit, damit nichts unbegrenzt haengt.
# Jeder Aufruf ist ein git-Aufruf; run_git bekommt nur die Subcommand-Argumente.
if command -v timeout >/dev/null 2>&1; then
  run_git() { timeout -k 2 "$TIMEOUT_SEC" git "$@"; }
else
  run_git() {
    git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime="$TIMEOUT_SEC" "$@"
  }
fi

# --- Default-Branch ermitteln, nicht "main" annehmen -----------------------
# Mindestens ein Repo im Portfolio nutzt "master"; genau die Annahme "main"
# hat schon einmal einen Branch 15 Commits alt werden lassen, weil der
# fest verdrahtete Fetch mit "couldn't find remote ref main" scheiterte und
# das fuer ein Netzproblem gehalten wurde.

# 1. Lokal gecachter Zeiger — kostet kein Netz, ist aber oft ungesetzt
#    (frische Klone von Claude Code on the web haben ihn regelmaessig nicht).
DEFAULT_BRANCH="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)"
DEFAULT_BRANCH="${DEFAULT_BRANCH#origin/}"

# 2. Sonst den Remote fragen (autoritativ, kostet einen Roundtrip).
if [ -z "$DEFAULT_BRANCH" ]; then
  DEFAULT_BRANCH="$(run_git ls-remote --symref origin HEAD 2>/dev/null \
    | sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p' | head -n 1)"
fi

# 3. Nicht ermittelbar -> still raus. Hier NICHT auf "main" zurueckfallen:
#    ein geratener Branchname erzeugt entweder einen Fehlalarm oder einen
#    stillen Fetch des Remote-HEAD, der mit 0 endet und nichts geprueft hat.
[ -n "$DEFAULT_BRANCH" ] || exit 0

# --- Fetch mit Deckel ------------------------------------------------------
run_git fetch --quiet origin "$DEFAULT_BRANCH" >/dev/null 2>&1 || exit 0

# --- Abstand messen --------------------------------------------------------
# Funktioniert auch bei detached HEAD. Schlaegt fehl bei ungeborenem HEAD
# (frisches Repo ohne Commit) — dann still raus.
BEHIND="$(git rev-list --count HEAD..FETCH_HEAD 2>/dev/null)"
case "$BEHIND" in
  ''|*[!0-9]*) exit 0 ;;
  0) exit 0 ;;
esac

COMMIT_WORT="Commits"
[ "$BEHIND" = "1" ] && COMMIT_WORT="Commit"

cat <<MSG
[Klon-Aktualitaet] Der ausgecheckte Stand liegt $BEHIND $COMMIT_WORT hinter origin/$DEFAULT_BRANCH.

Vor der Arbeit aktualisieren, sonst droht eine rote CI, deren Ursache nicht im
Diff steht: fehlende Commits sind haeufig genau die, die ein neues Gate
einfuehren, an dem der Branch dann scheitert.

    git merge FETCH_HEAD          # oder: git rebase origin/$DEFAULT_BRANCH
MSG

exit 0
