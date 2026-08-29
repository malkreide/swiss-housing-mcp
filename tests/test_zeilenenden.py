#!/usr/bin/env python3
"""Der Baum behaelt LF-Zeilenenden — auch auf Windows.

Git fuer Windows setzt `core.autocrlf=true` als Vorgabe und checkt Textdateien
dort mit CRLF aus. Ein Shell-Skript ueberlebt das nicht: bash liest das `\\r`
als Teil des Befehls und bricht in Zeile 1 ab.

    set: pipefail: invalid option name
    $'\\r': command not found
    syntax error near unexpected token `$'in\\r''

Am 29.8.2026 genau so passiert. Der Punkt daran ist die Sichtbarkeit: Im Repo
lagen die Dateien mit LF, kaputt war erst der Klon. Die CI laeuft auf Linux, wo
nicht konvertiert wird — sie kann den Fehler also gar nicht sehen.

Was diese Tests koennen und was nicht:

  - `test_gitattributes_nagelt_die_textarten_fest` prueft die Regeln, die den
    Windows-Klon schuetzen. Das ist der tragende Test: Verschwindet eine Regel
    oder steht sie auf `eol=crlf`, faellt er, und zwar auf jedem
    Betriebssystem.
  - `test_kein_crlf_im_baum` prueft den Baum selbst und faengt eine Datei ab,
    die mit CRLF eingecheckt wird. Solange die Regeln oben stehen, kann er
    kaum rot werden; er ist die zweite Reihe, nicht der Beleg.

Der Umfang folgt `.gitattributes` statt einer eigenen Liste. Sonst waechst die
Regeldatei, und der Test prueft weiter den alten Ausschnitt — er wuerde immer
gruener, je mehr abgedeckt ist.

Geschichte: Bis zum 29.8.2026 sah der zweite Test nur in `scripts/*.sh`. Als
die beiden Migrationsskripte dort geloescht wurden, waere er auf eine leere
Menge gelaufen und haette weiter gruen gemeldet — gefangen hat das nur die
Zusicherung, dass die Suche ueberhaupt Dateien sieht. Die steht deshalb immer
noch da, jetzt fuer den ganzen Baum.
"""

from __future__ import annotations

import pathlib
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_ATTRIBUTE = _ROOT / ".gitattributes"

# Verzeichnisse, die nicht im Repo stehen und deren Inhalt niemandem gehoert.
_IGNORIERT = {".git", "__pycache__", ".ruff_cache", ".pytest_cache", ".venv", "node_modules"}


def _regeln() -> dict[str, list[str]]:
    zeilen = [
        z.split("#", 1)[0].split() for z in _ATTRIBUTE.read_text(encoding="utf-8").splitlines()
    ]
    return {teile[0]: teile[1:] for teile in zeilen if teile}


def _dateien(muster: list[str]) -> list[pathlib.Path]:
    treffer: list[pathlib.Path] = []
    for m in muster:
        treffer += [
            p
            for p in _ROOT.rglob(m)
            if p.is_file() and not _IGNORIERT.intersection(p.relative_to(_ROOT).parts)
        ]
    return sorted(set(treffer))


class ZeilenendenTest(unittest.TestCase):
    def test_gitattributes_nagelt_die_textarten_fest(self) -> None:
        self.assertTrue(_ATTRIBUTE.is_file(), ".gitattributes fehlt")
        regeln = _regeln()
        # `*.sh` einzeln benannt: Das ist die Art, bei der ein CRLF-Checkout
        # nicht bloss den Diff verschmutzt, sondern die Datei unbrauchbar
        # macht. `.claude/hooks/session-start.sh` haengt daran.
        for muster in ("*.sh", "*.py", "*.yml", "*.yaml", "*.md", "*.toml", "*.json"):
            self.assertIn(muster, regeln, f"keine Regel fuer {muster}")
            self.assertIn(
                "eol=lf",
                regeln[muster],
                f"{muster} ist nicht auf LF festgenagelt; ein Windows-Klon bekommt "
                f"solche Dateien mit CRLF",
            )

    def test_kein_crlf_im_baum(self) -> None:
        muster = [m for m in _regeln() if m.startswith("*.")]
        gefunden = [
            str(p.relative_to(_ROOT)) for p in _dateien(muster) if b"\r\n" in p.read_bytes()
        ]
        self.assertEqual(gefunden, [], "Dateien mit CRLF im Baum")

    def test_die_suche_sieht_ueberhaupt_dateien(self) -> None:
        """Gegenprobe zum Test darueber: Eine leere Menge ist kein Ergebnis.

        Genau hier haette es am 29.8.2026 gehakt — der Vorgaenger sah nur in
        `scripts/*.sh`, und mit dem Loeschen der Migrationsskripte waere dieses
        Verzeichnis leer gewesen. Ohne diese Zusicherung haette der CRLF-Test
        von da an nichts mehr geprueft und es nicht gesagt.
        """
        muster = [m for m in _regeln() if m.startswith("*.")]
        self.assertGreater(len(_dateien(muster)), 10)
        self.assertTrue(_dateien(["*.sh"]), "kein einziges Shell-Skript gefunden")


if __name__ == "__main__":
    unittest.main()
