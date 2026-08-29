#!/usr/bin/env python3
r"""Deklarierte Dependabot-Labels gegen die tatsaechlich vorhandenen halten.

Das ist der Check, der am 29.8.2026 gefehlt hat. Die Ausgangslage war ein
Kommentar, den Dependabot an jeden Pull Request haengt:

    The following labels could not be found: `dependencies`, `python`.

Kein roter Check, kein Log — nur diese Zeile, in jedem betroffenen Repo, teils
seit Monaten. Niemand faellt darueber, weil nichts sie meldet.

WAS DER CHECK BEURTEILT

Die Optionsreferenz von Dependabot regelt zwei Dinge, und beide zaehlen hier:

    All pull requests have a `dependencies` label. If you define more than one
    package manager, an additional label for the ecosystem or language is added
    to each pull request. [...] Dependabot creates these default labels
    automatically, as necessary in your repository.

    If any of these labels is not defined in the repository, it is ignored.

Daraus folgen die drei Urteile unten:

  SAUBER    Keine `labels:`-Zeile. Dann gilt der Vorgabesatz, und der legt sich
            selbst an. Das ist der Zielzustand, nicht bloss die Abwesenheit
            eines Problems.
  HINWEIS   Eine `labels:`-Zeile, deren Namen alle existieren. Funktioniert —
            ersetzt aber den Vorgabesatz und muss von Hand synchron gehalten
            werden. Kein Defekt, nur Wartungslast.
  DEFEKT    Eine `labels:`-Zeile mit mindestens einem Namen, den das Repo nicht
            kennt. Dependabot ignoriert ihn und quittiert es mit dem Kommentar
            oben.

Nur DEFEKT setzt den Exit-Code auf 1. Ein HINWEIS ist eine Beobachtung, keine
Fehlermeldung — wer beides gleich behandelt, bekommt eine Ausgabe, die man
wegklickt.

WARUM NICHT BLOSS «gibt es das Label»

Weil die Frage in beide Richtungen falsch beantwortet wurde. Erst hiess es,
Dependabot lege Labels nicht an und die Zeile sei wirkungslos; dann wurde
gemessen, dass `dependencies` in sieben von zehn Repos existiert, und das als
Widerspruch gelesen. Beides war daneben: Die vorhandenen Labels waren von
Dependabot selbst angelegt, und die Zeile war nicht wirkungslos, sondern
schaedlich. Ein Check, der nur zaehlt, welche Labels es gibt, haette beide
Fehlschluesse zugelassen. Dieser hier vergleicht deklariert gegen vorhanden
und sagt, was daraus folgt.

Verwendung:
    python pruefe_dependabot_labels.py                      # alle *-mcp
    python pruefe_dependabot_labels.py amtsblatt-mcp ...    # nur diese

Exit-Codes:
    0  kein DEFEKT
    1  mindestens ein deklariertes Label existiert nicht
    2  Fehler (kein `gh`, Abfrage fehlgeschlagen, Datei parst nicht)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterable
from typing import Any, NamedTuple

import yaml

OWNER = "malkreide"

SAUBER = "SAUBER"
HINWEIS = "HINWEIS"
DEFEKT = "DEFEKT"
OHNE_DATEI = "OHNE DATEI"


class Befund(NamedTuple):
    repo: str
    urteil: str
    deklariert: frozenset[str]
    fehlend: frozenset[str]


def deklarierte_labels(text: str) -> set[str]:
    """Alle Namen, die irgendein `labels:` in der Datei auffuehrt.

    Bewusst ueber den Parser und nicht ueber einen regulaeren Ausdruck: Hier
    wird gelesen, nicht geschnitten, also kostet ein YAML-Round-Trip nichts.
    Das Migrationsskript, das die Zeilen 2026 entfernt hat, hatte den
    umgekehrten Fall — es musste Kommentare und Formatierung erhalten und
    schnitt deshalb zeilenweise.
    """

    def sammle(knoten: Any) -> Iterable[str]:
        if isinstance(knoten, dict):
            for schluessel, wert in knoten.items():
                if schluessel == "labels":
                    if isinstance(wert, list):
                        yield from (str(v) for v in wert)
                    elif wert is not None:
                        yield str(wert)
                else:
                    yield from sammle(wert)
        elif isinstance(knoten, list):
            for eintrag in knoten:
                yield from sammle(eintrag)

    return set(sammle(yaml.safe_load(text)))


def einordnen(repo: str, text: str | None, vorhanden: set[str]) -> Befund:
    """Ein Repo beurteilen. `text is None` heisst: keine `dependabot.yml`."""
    if text is None:
        return Befund(repo, OHNE_DATEI, frozenset(), frozenset())
    deklariert = deklarierte_labels(text)
    if not deklariert:
        return Befund(repo, SAUBER, frozenset(), frozenset())
    fehlend = deklariert - vorhanden
    return Befund(repo, DEFEKT if fehlend else HINWEIS, frozenset(deklariert), frozenset(fehlend))


def _gh(args: list[str]) -> str:
    ergebnis = subprocess.run(  # noqa: S603
        ["gh", *args], capture_output=True, text=True, check=False
    )
    if ergebnis.returncode != 0:
        raise RuntimeError(ergebnis.stderr.strip() or f"gh {' '.join(args)} fehlgeschlagen")
    return ergebnis.stdout


def hole_von_github(repo: str) -> tuple[str | None, set[str]]:
    """`(inhalt der dependabot.yml oder None, vorhandene Labels)`."""
    try:
        text: str | None = _gh(
            [
                "api",
                "-H",
                "Accept: application/vnd.github.raw",
                f"repos/{OWNER}/{repo}/contents/.github/dependabot.yml",
            ]
        )
    except RuntimeError as exc:
        # Eine fehlende Datei ist kein Fehler, sondern ein Zustand. Alles
        # andere schon — sonst zaehlt eine kaputte Abfrage als «nichts da».
        if "404" not in str(exc) and "Not Found" not in str(exc):
            raise
        text = None
    roh = _gh(["api", f"repos/{OWNER}/{repo}/labels", "--paginate"])
    return text, {eintrag["name"] for eintrag in json.loads(roh)}


def alle_repos() -> list[str]:
    roh = _gh(
        ["repo", "list", OWNER, "--limit", "300", "--no-archived", "--source", "--json", "name"]
    )
    return sorted(e["name"] for e in json.loads(roh) if e["name"].endswith("-mcp"))


def bericht(repos: list[str], hole: Callable[[str], tuple[str | None, set[str]]]) -> list[Befund]:
    befunde = []
    for repo in repos:
        text, vorhanden = hole(repo)
        befunde.append(einordnen(repo, text, vorhanden))
    return befunde


def _zeilen(befunde: list[Befund]) -> Iterable[str]:
    for b in sorted(befunde, key=lambda b: (b.urteil != DEFEKT, b.repo)):
        if b.urteil == DEFEKT:
            yield f"  DEFEKT   {b.repo}: fehlt {', '.join(sorted(b.fehlend))}"
        elif b.urteil == HINWEIS:
            yield f"  HINWEIS  {b.repo}: deklariert {', '.join(sorted(b.deklariert))} (alle da)"
        elif b.urteil == OHNE_DATEI:
            yield f"  ---      {b.repo}: keine dependabot.yml"
        else:
            yield f"  sauber   {b.repo}"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("repos", nargs="*", help="Repo-Namen; ohne Angabe alle *-mcp des Kontos")
    args = p.parse_args()

    if shutil.which("gh") is None:
        print("FEHLER: gh nicht gefunden", file=sys.stderr)
        return 2
    try:
        repos = args.repos or alle_repos()
        if not repos:
            print("FEHLER: keine Repos ermittelt — Abbruch statt leerem Lauf", file=sys.stderr)
            return 2
        befunde = bericht(repos, hole_von_github)
    except (RuntimeError, yaml.YAMLError) as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2

    print("\n".join(_zeilen(befunde)))
    zahl = {
        u: sum(1 for b in befunde if b.urteil == u) for u in (DEFEKT, HINWEIS, SAUBER, OHNE_DATEI)
    }
    print(
        f"\nDEFEKT: {zahl[DEFEKT]}   HINWEIS: {zahl[HINWEIS]}   "
        f"sauber: {zahl[SAUBER]}   ohne Datei: {zahl[OHNE_DATEI]}"
    )
    if zahl[DEFEKT]:
        print(
            "\nEin DEFEKT heisst: Dependabot ignoriert den Namen und haengt an jeden PR\n"
            "den Kommentar «The following labels could not be found». Die Zeile ganz zu\n"
            "streichen stellt den Vorgabesatz her, der sich selbst anlegt."
        )
    return 1 if zahl[DEFEKT] else 0


if __name__ == "__main__":
    sys.exit(main())
