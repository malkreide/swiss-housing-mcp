#!/usr/bin/env python3
"""Tests fuer scripts/pruefe_dependabot_labels.py — die drei Urteile.

Der Check unterscheidet SAUBER, HINWEIS und DEFEKT. Die Unterscheidung ist
sein ganzer Zweck, also faellt sie hier einzeln aus:

  - SAUBER heisst «keine `labels:`-Zeile», nicht «keine fehlenden Labels».
    Wer beides zusammenlegt, meldet ein Repo mit vollstaendig existierenden
    Labels als in Ordnung — dabei traegt es dann eine Liste, die den
    Vorgabesatz ersetzt und von Hand gepflegt werden muss.
  - HINWEIS darf den Exit-Code NICHT auf 1 setzen. Sonst ist jeder Lauf rot,
    solange irgendwo eine funktionierende Liste steht, und die Ausgabe wird
    weggeklickt — genau der Zustand, gegen den der Check antritt.
  - DEFEKT muss ihn setzen, sonst ist er kein Gate.

Die Abfrage gegen GitHub ist ueber `bericht(repos, hole)` eingehaengt und wird
hier durch ein Woerterbuch ersetzt. Ohne diese Naht liesse sich das Urteil nur
gegen das echte Konto pruefen, also gar nicht.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import pruefe_dependabot_labels as pdl  # noqa: E402

_MIT_LISTE = """\
version: 2
updates:
  - package-ecosystem: "pip"
    labels: ["dependencies", "python"]
  - package-ecosystem: "github-actions"
    labels:
      - "dependencies"
      - "ci"
"""

_OHNE_LISTE = """\
version: 2
updates:
  - package-ecosystem: "pip"
    schedule:
      interval: "monthly"
"""


class DeklarierteLabelsTest(unittest.TestCase):
    def test_inline_und_block_zusammen(self) -> None:
        self.assertEqual(pdl.deklarierte_labels(_MIT_LISTE), {"dependencies", "python", "ci"})

    def test_ohne_liste_ist_leer(self) -> None:
        self.assertEqual(pdl.deklarierte_labels(_OHNE_LISTE), set())

    def test_labels_tiefer_im_baum_werden_gefunden(self) -> None:
        """`labels:` steht nicht immer direkt unter einem `updates`-Eintrag.

        Ohne die Rekursion faende der Check nur die oberste Ebene und meldete
        ein Repo als sauber, das eine Liste fuehrt.
        """
        text = 'version: 2\nupdates:\n  - a:\n      b:\n        labels: ["tief"]\n'
        self.assertEqual(pdl.deklarierte_labels(text), {"tief"})

    def test_einzelner_wert_statt_liste(self) -> None:
        self.assertEqual(pdl.deklarierte_labels("labels: allein\n"), {"allein"})


class UrteilTest(unittest.TestCase):
    def test_ohne_liste_ist_sauber(self) -> None:
        b = pdl.einordnen("r", _OHNE_LISTE, {"dependencies"})
        self.assertEqual(b.urteil, pdl.SAUBER)

    def test_alle_vorhanden_ist_hinweis_nicht_sauber(self) -> None:
        """Eine funktionierende Liste ist kein Defekt — aber auch nicht sauber.

        Sie ersetzt den Vorgabesatz, der sich selbst anlegt, durch eine
        Aufzaehlung, die jemand pflegen muss. Genau diese Unterscheidung hat
        am 29.8.2026 gefehlt.
        """
        b = pdl.einordnen("r", _MIT_LISTE, {"dependencies", "python", "ci"})
        self.assertEqual(b.urteil, pdl.HINWEIS)
        self.assertEqual(b.fehlend, frozenset())

    def test_ein_fehlender_name_ist_defekt(self) -> None:
        b = pdl.einordnen("r", _MIT_LISTE, {"dependencies"})
        self.assertEqual(b.urteil, pdl.DEFEKT)
        self.assertEqual(b.fehlend, frozenset({"python", "ci"}))

    def test_keine_datei_ist_eigener_zustand(self) -> None:
        b = pdl.einordnen("r", None, set())
        self.assertEqual(b.urteil, pdl.OHNE_DATEI)


class BerichtUndExitCodeTest(unittest.TestCase):
    def lauf(self, welt: dict[str, tuple[str | None, set[str]]]) -> int:
        alt_argv = sys.argv
        sys.argv = ["pruefe_dependabot_labels.py", *welt]
        try:
            # `shutil.which` und die echte Abfrage sind die beiden Nahtstellen
            # nach draussen; beide werden hier ersetzt.
            alt_which, alt_hole = pdl.shutil.which, pdl.hole_von_github
            pdl.shutil.which = lambda _: "/usr/bin/gh"  # type: ignore[assignment]
            pdl.hole_von_github = welt.__getitem__  # type: ignore[assignment]
            try:
                return pdl.main()
            finally:
                pdl.shutil.which, pdl.hole_von_github = alt_which, alt_hole
        finally:
            sys.argv = alt_argv

    def test_nur_sauber_und_hinweis_ist_exit_null(self) -> None:
        code = self.lauf(
            {
                "a-mcp": (_OHNE_LISTE, {"dependencies"}),
                "b-mcp": (_MIT_LISTE, {"dependencies", "python", "ci"}),
                "c-mcp": (None, set()),
            }
        )
        self.assertEqual(code, 0)

    def test_ein_defekt_ist_exit_eins(self) -> None:
        code = self.lauf(
            {"a-mcp": (_OHNE_LISTE, {"dependencies"}), "b-mcp": (_MIT_LISTE, {"dependencies"})}
        )
        self.assertEqual(code, 1)

    def test_bericht_ordnet_jedem_repo_ein_urteil_zu(self) -> None:
        welt: dict[str, tuple[str | None, set[str]]] = {
            "a-mcp": (_OHNE_LISTE, set()),
            "b-mcp": (_MIT_LISTE, {"dependencies"}),
        }
        befunde = pdl.bericht(list(welt), welt.__getitem__)
        self.assertEqual([b.repo for b in befunde], ["a-mcp", "b-mcp"])
        self.assertEqual([b.urteil for b in befunde], [pdl.SAUBER, pdl.DEFEKT])


if __name__ == "__main__":
    unittest.main()
