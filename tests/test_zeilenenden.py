#!/usr/bin/env python3
"""Die Shell-Skripte muessen LF-Zeilenenden behalten — auch auf Windows.

Git fuer Windows setzt `core.autocrlf=true` als Vorgabe und checkt Textdateien
dort mit CRLF aus. Ein Shell-Skript ueberlebt das nicht: bash liest das `\\r`
als Teil des Befehls und bricht in Zeile 1 ab.

    set: pipefail: invalid option name
    $'\\r': command not found
    syntax error near unexpected token `$'in\\r''

Am 29.8.2026 genau so passiert. Der Punkt daran ist die Sichtbarkeit: Im Repo
lagen die Dateien mit LF, kaputt war erst der Klon. Die CI laeuft auf Linux,
wo nicht konvertiert wird — sie kann den Fehler also gar nicht sehen.

Was diese Tests deshalb koennen und was nicht:

  - `test_gitattributes_nagelt_shell_skripte_fest` prueft die Regel, die den
    Windows-Klon schuetzt. Das ist der tragende Test: Verschwindet die Regel,
    faellt er, und zwar auf jedem Betriebssystem.
  - `test_kein_crlf_in_den_skripten` prueft den Baum selbst. Er faengt eine
    Datei ab, die mit CRLF eingecheckt wird — mehr nicht. Solange die Regel
    oben steht, kann er kaum rot werden; er ist die zweite Reihe, nicht der
    Beleg.

Wer nur den zweiten schriebe, haette einen Test, der auf der Testmaschine
nicht falsch werden kann, und keinen fuer die Ursache.
"""

from __future__ import annotations

import pathlib
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_ATTRIBUTE = _ROOT / ".gitattributes"


class ZeilenendenTest(unittest.TestCase):
    def test_gitattributes_nagelt_shell_skripte_fest(self) -> None:
        self.assertTrue(_ATTRIBUTE.is_file(), ".gitattributes fehlt")
        zeilen = [
            z.split("#", 1)[0].split() for z in _ATTRIBUTE.read_text(encoding="utf-8").splitlines()
        ]
        regeln = {teile[0]: teile[1:] for teile in zeilen if teile}
        self.assertIn("*.sh", regeln, "keine Regel fuer Shell-Skripte")
        self.assertIn(
            "eol=lf",
            regeln["*.sh"],
            "Shell-Skripte sind nicht auf LF festgenagelt; ein Windows-Klon "
            "bekommt sie mit CRLF und bash bricht in Zeile 1 ab",
        )

    def test_kein_crlf_in_den_skripten(self) -> None:
        gefunden = [
            str(p.relative_to(_ROOT))
            for p in sorted((_ROOT / "scripts").glob("*.sh"))
            if b"\r\n" in p.read_bytes()
        ]
        self.assertEqual(gefunden, [], "Shell-Skripte mit CRLF im Baum")

    def test_es_gibt_ueberhaupt_shell_skripte(self) -> None:
        """Gegenprobe zum Test darueber: Eine leere Liste ist kein Ergebnis.

        Ohne diese Zusicherung bliebe `test_kein_crlf_in_den_skripten` gruen,
        wenn das Verzeichnis umbenannt wird oder die Skripte verschwinden — er
        prueft dann nichts und sagt es nicht.
        """
        self.assertNotEqual(list((_ROOT / "scripts").glob("*.sh")), [])


if __name__ == "__main__":
    unittest.main()
