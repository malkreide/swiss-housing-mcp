#!/usr/bin/env python3
"""`labels:` aus einer `.github/dependabot.yml` entfernen — inline wie Block.

Hintergrund: Dependabot legt Labels nicht an. Steht unter `labels:` ein Name,
den das Repo nicht kennt, haengt es nur einen Kommentar an jeden Pull Request
und laesst ihn ungelabelt — kein roter Check, kein Log. Ein Gate dagegen kann
es nicht geben, weil Labels GitHub-Zustand sind und kein Dateiinhalt.

Die Information ist ohnehin doppelt vorhanden: der Autor (`dependabot[bot]`),
das Commit-Prefix (`deps`/`ci`/`docker`) und der Branchname nennen dasselbe.

Verwendung:
    python entferne_dependabot_labels.py --dry-run PFAD...   # nur zeigen
    python entferne_dependabot_labels.py PFAD...             # schreiben

Exit-Codes — das Wrapper-Skript unterscheidet daran drei Faelle:
    0  mindestens eine Datei wurde geaendert (bzw. wuerde bei --dry-run)
    1  nichts zu tun: keine der Dateien fuehrt `labels:`
    2  FEHLER: Datei fehlt, Ergebnis nicht verifizierbar, oder ein `labels:`
       ist vorhanden, aber von den Mustern unten nicht erfasst worden

Geschrieben wird zeilenweise und nicht ueber einen YAML-Round-Trip: der
wuerde Kommentare und Formatierung verlieren, und genau die sind hier der
wertvollste Teil der Datei — sie traegt in mehreren Repos einen langen
erklaerenden Kopf.

GEPRUEFT wird dagegen sehr wohl mit einem YAML-Parser, und zwar semantisch:
das Ergebnis muss parsen, es darf kein `labels:` mehr enthalten, und es muss
ansonsten Zeichen fuer Zeichen dieselbe Struktur ergeben wie vorher. Ohne
diese Gegenprobe ist das Skript blind fuer genau den Fall, der es kaputt
macht — ein Kommentar zwischen `labels:` und seiner Liste laesst die
Eintraege verwaist zurueck und macht die Datei unparsbar, ohne dass irgendein
Check im Repo rot wird. Dependabot stellt dann still den Betrieb ein.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - haengt an der Umgebung
    yaml = None

# Inline-Form. Der Zeilenkommentar am Ende ist Teil des Musters: `labels: [a]
# # siehe README` wurde ohne ihn nicht erkannt, und das Skript meldete dann
# faelschlich «kein labels:» — ein stiller Aussetzer statt eines Fehlers.
_LABELS_INLINE = re.compile(r"^(\s*)labels:\s*\[[^\]]*\]\s*(#.*)?$")
_LABELS_BLOCK = re.compile(r"^(\s*)labels:\s*(#.*)?$")
_LIST_ITEM = re.compile(r"^(\s*)-\s*\S")
_KOMMENTAR = re.compile(r"^(\s*)#")


def _folgt_noch_ein_eintrag(lines: list[str], j: int, indent: int) -> int | None:
    """Index des naechsten Listeneintrags ab `j`, wenn nur Leerzeilen und
    Kommentare dazwischen liegen. Sonst `None`.

    Damit werden Leerzeilen und Kommentare INNERHALB der Liste mitgenommen,
    die dahinter aber nicht: ein Kommentar, der schon den naechsten Schluessel
    erklaert, bleibt stehen.
    """
    while j < len(lines):
        nackt = lines[j].rstrip("\n")
        if not nackt.strip() or _KOMMENTAR.match(nackt):
            j += 1
            continue
        m = _LIST_ITEM.match(nackt)
        # `>=`, nicht `>`: In YAML darf ein Listeneintrag auf derselben Spalte
        # stehen wie sein Schluessel, und beide Schreibweisen kommen im
        # Portfolio vor.
        if m and len(m.group(1)) >= indent:
            return j
        return None
    return None


def entferne_labels(text: str) -> tuple[str, int]:
    """Gibt `(neuer_text, entfernte_schluessel)` zurueck."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    entfernt = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        nackt = line.rstrip("\n")

        if _LABELS_INLINE.match(nackt):
            entfernt += 1
            i += 1
            continue

        block = _LABELS_BLOCK.match(nackt)
        if block:
            indent = len(block.group(1))
            entfernt += 1
            i += 1
            while i < len(lines):
                roh = lines[i].rstrip("\n")
                m = _LIST_ITEM.match(roh)
                if m and len(m.group(1)) >= indent:
                    i += 1
                    continue
                # Leerzeile oder Kommentar: nur schlucken, wenn danach noch
                # ein Eintrag derselben Liste kommt.
                if not roh.strip() or _KOMMENTAR.match(roh):
                    weiter = _folgt_noch_ein_eintrag(lines, i, indent)
                    if weiter is None:
                        break
                    i = weiter
                    continue
                break
            continue

        out.append(line)
        i += 1

    return "".join(out), entfernt


def _ohne_labels(knoten: Any) -> Any:
    """Kopie der Struktur, aus der jedes `labels`-Mapping-Feld entfernt ist."""
    if isinstance(knoten, dict):
        return {k: _ohne_labels(v) for k, v in knoten.items() if k != "labels"}
    if isinstance(knoten, list):
        return [_ohne_labels(v) for v in knoten]
    return knoten


def _hat_labels(knoten: Any) -> bool:
    if isinstance(knoten, dict):
        return "labels" in knoten or any(_hat_labels(v) for v in knoten.values())
    if isinstance(knoten, list):
        return any(_hat_labels(v) for v in knoten)
    return False


def pruefe(alt: str, neu: str) -> str | None:
    """Semantische Gegenprobe. Gibt den Grund zurueck, falls etwas nicht stimmt.

    Drei Zusicherungen, jede einzeln noetig:
      1. Das Ergebnis parst ueberhaupt noch.
      2. Es fuehrt kein `labels` mehr.
      3. Alles uebrige ist unveraendert — der Schnitt hat nur `labels` erwischt.
    """
    if yaml is None:
        return "pyyaml fehlt, das Ergebnis ist nicht ueberpruefbar (pip install pyyaml)"
    try:
        vorher = yaml.safe_load(alt)
    except yaml.YAMLError as exc:
        return f"schon die Ausgangsdatei parst nicht: {exc.__class__.__name__}"
    try:
        nachher = yaml.safe_load(neu)
    except yaml.YAMLError as exc:
        return f"Ergebnis parst nicht mehr: {exc.__class__.__name__}"
    if _hat_labels(nachher):
        return "nach dem Schnitt steht immer noch ein `labels` in der Datei"
    if _ohne_labels(vorher) != nachher:
        return "der Schnitt hat mehr als `labels` veraendert"
    return None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pfade", nargs="+", type=Path)
    p.add_argument("--dry-run", action="store_true", help="nur berichten, nichts schreiben")
    args = p.parse_args()

    gesamt = 0
    fehler = 0
    for pfad in args.pfade:
        if not pfad.exists():
            print(f"{pfad}: nicht vorhanden", file=sys.stderr)
            fehler += 1
            continue
        alt = pfad.read_text(encoding="utf-8")
        neu, n = entferne_labels(alt)

        if n == 0:
            # Nicht blind «nichts zu tun» melden: Wenn die Datei ein `labels`
            # fuehrt, das die Muster oben nicht getroffen haben, ist das ein
            # Fehler und keine Ruhe. Genau so ist die Inline-Form mit
            # Zeilenkommentar frueher durchgerutscht.
            if yaml is not None:
                try:
                    if _hat_labels(yaml.safe_load(alt)):
                        print(
                            f"{pfad}: FEHLER — `labels` vorhanden, aber von keinem Muster "
                            f"erfasst; bitte von Hand ansehen",
                            file=sys.stderr,
                        )
                        fehler += 1
                        continue
                except yaml.YAMLError:
                    print(f"{pfad}: FEHLER — parst nicht", file=sys.stderr)
                    fehler += 1
                    continue
            print(f"{pfad}: kein `labels:` — unveraendert")
            continue

        grund = pruefe(alt, neu)
        if grund:
            print(f"{pfad}: FEHLER — {grund}; nichts geschrieben", file=sys.stderr)
            fehler += 1
            continue

        gesamt += n
        if args.dry_run:
            zeilen = len(alt.splitlines()) - len(neu.splitlines())
            print(f"{pfad}: {n} `labels:`-Schluessel wuerden entfernt ({zeilen} Zeilen)")
        else:
            pfad.write_text(neu, encoding="utf-8")
            print(f"{pfad}: {n} `labels:`-Schluessel entfernt")

    if fehler:
        return 2
    return 0 if gesamt else 1


if __name__ == "__main__":
    sys.exit(main())
