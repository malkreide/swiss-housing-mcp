#!/usr/bin/env python3
"""Tests fuer scripts/entferne_dependabot_labels.py — der Schnitt und sein Netz.

Das Skript schneidet mit regulaeren Ausdruecken in eine YAML-Datei. Das ist
Absicht: Ein Round-Trip durch einen YAML-Serializer wuerde die langen
erklaerenden Koepfe verlieren, die diese Dateien im Portfolio tragen. Der
Preis dafuer ist, dass ein Muster danebengreifen kann.

Zwei Faelle haben in der Vorgaengerfassung danebengegriffen, und beide waren
still:

  - Ein Kommentar ZWISCHEN `labels:` und seiner Liste (Fall D unten). Der
    Schluessel fiel, die Eintraege blieben verwaist stehen, die Datei war
    nicht mehr parsbar. Dependabot stellt dann in dem Repo den Betrieb ein,
    ohne dass irgendein Check rot wird — genau die Ausfallklasse, gegen die
    das Skript ueberhaupt antritt.
  - Die Inline-Form mit Zeilenkommentar (Fall E). Sie traf kein Muster, das
    Skript meldete «kein `labels:`», und das Wrapper-Skript buchte das Repo
    als erledigt ab.

Deshalb pruefen die Tests hier nicht nur, dass der erwartete Text herauskommt,
sondern in jedem Fall zusaetzlich, dass das ERGEBNIS PARST und kein `labels`
mehr fuehrt. Ein Test, der bloss Zeilen vergleicht, haette Fall D bestanden.

Die letzten Tests gelten `pruefe()` selbst — dem Netz, das auch dann noch
haelt, wenn ein Muster einen hier nicht aufgeschriebenen Fall verfehlt. Ohne
sie waere die Zusicherung «kaputte Datei wird nie geschrieben» ungeprueft.

Nur Standardbibliothek plus pyyaml, kein Netz.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import entferne_dependabot_labels as edl  # noqa: E402

_KOPF = """\
# Dependabot — monatliche Update-PRs.
#
# Dieser Kopf ist der wertvollste Teil der Datei und muss stehen bleiben.
version: 2
updates:
"""


def _mit_kopf(rumpf: str) -> str:
    return _KOPF + rumpf


class SchnittTest(unittest.TestCase):
    """Jeder Fall: erwarteter Text, Datei parst, kein `labels` mehr, Kopf steht."""

    def schneide(self, text: str, erwartet_entfernt: int = 1) -> str:
        neu, n = edl.entferne_labels(text)
        self.assertEqual(n, erwartet_entfernt, "Zahl der entfernten Schluessel")
        # Die eigentliche Zusicherung. Ein reiner Textvergleich haette den
        # Kommentar-Fall unten durchgelassen.
        geladen = yaml.safe_load(neu)
        self.assertFalse(edl._hat_labels(geladen), f"labels steht noch drin:\n{neu}")
        self.assertIn("Dieser Kopf ist der wertvollste Teil", neu, "Kopf verloren")
        self.assertIsNone(edl.pruefe(text, neu), "pruefe() beanstandet das Ergebnis")
        return neu

    def test_inline(self) -> None:
        neu = self.schneide(
            _mit_kopf(
                '  - package-ecosystem: "pip"\n'
                '    directory: "/"\n'
                '    labels: ["dependencies", "python"]\n'
                "    schedule:\n"
                '      interval: "monthly"\n'
            )
        )
        self.assertNotIn("labels", neu)

    def test_block_eingerueckt(self) -> None:
        self.schneide(
            _mit_kopf(
                '  - package-ecosystem: "pip"\n'
                "    labels:\n"
                "      - dependencies\n"
                "      - python\n"
                "    schedule:\n"
                '      interval: "monthly"\n'
            )
        )

    def test_block_auf_gleicher_spalte(self) -> None:
        """In YAML darf der Eintrag auf derselben Spalte stehen wie sein Schluessel.

        Beide Schreibweisen kommen im Portfolio vor; `>` statt `>=` beim
        Einrueckungsvergleich laesst diese hier stehen.
        """
        self.schneide(
            _mit_kopf(
                '  - package-ecosystem: "pip"\n'
                "    labels:\n"
                "    - dependencies\n"
                "    - python\n"
                "    schedule:\n"
                '      interval: "monthly"\n'
            )
        )

    def test_kommentar_zwischen_schluessel_und_liste(self) -> None:
        """Fall D — der Fall, der die Datei unparsbar zurueckliess."""
        neu = self.schneide(
            _mit_kopf(
                '  - package-ecosystem: "pip"\n'
                "    labels:\n"
                "      # so werden die PRs einsortiert\n"
                "      - dependencies\n"
                "      - python\n"
                "    schedule:\n"
                '      interval: "monthly"\n'
            )
        )
        self.assertNotIn("so werden die PRs einsortiert", neu, "Kommentar der Liste blieb stehen")
        self.assertNotIn("- dependencies", neu, "verwaister Listeneintrag")

    def test_inline_mit_zeilenkommentar(self) -> None:
        """Fall E — traf kein Muster, meldete faelschlich «nichts zu tun»."""
        neu = self.schneide(
            _mit_kopf(
                '  - package-ecosystem: "pip"\n'
                '    labels: ["dependencies"]  # siehe README\n'
                "    schedule:\n"
                '      interval: "monthly"\n'
            )
        )
        self.assertNotIn("siehe README", neu)

    def test_labels_als_letzter_schluessel(self) -> None:
        self.schneide(
            _mit_kopf(
                '  - package-ecosystem: "pip"\n'
                "    schedule:\n"
                '      interval: "monthly"\n'
                "    labels:\n"
                "      - dependencies\n"
            )
        )

    def test_kommentar_nach_der_liste_bleibt_stehen(self) -> None:
        """Gegenstueck zu Fall D: ein Kommentar, der schon den naechsten
        Schluessel erklaert, gehoert nicht zur Liste und muss ueberleben.

        Ohne diese Unterscheidung wuerde die Kommentar-Behandlung aus Fall D
        zu gierig und frisst fremde Zeilen.
        """
        neu = self.schneide(
            _mit_kopf(
                '  - package-ecosystem: "pip"\n'
                "    labels:\n"
                "      - dependencies\n"
                "    # monatlich reicht, das Repo bewegt sich langsam\n"
                "    schedule:\n"
                '      interval: "monthly"\n'
            )
        )
        self.assertIn("monatlich reicht", neu, "fremder Kommentar wurde mitgenommen")

    def test_mehrere_eintraege(self) -> None:
        self.schneide(
            _mit_kopf(
                '  - package-ecosystem: "pip"\n'
                '    labels: ["dependencies"]\n'
                "    schedule:\n"
                '      interval: "monthly"\n'
                '  - package-ecosystem: "github-actions"\n'
                "    labels:\n"
                "      - ci\n"
                "    schedule:\n"
                '      interval: "monthly"\n'
            ),
            erwartet_entfernt=2,
        )

    def test_datei_ohne_labels_bleibt_unangetastet(self) -> None:
        text = _mit_kopf('  - package-ecosystem: "pip"\n    schedule:\n      interval: "monthly"\n')
        neu, n = edl.entferne_labels(text)
        self.assertEqual(n, 0)
        self.assertEqual(neu, text)


class PruefungTest(unittest.TestCase):
    """`pruefe()` ist das Netz unter den Mustern — hier faellt es einzeln aus.

    Jede der drei Zusicherungen wird mit einem Ergebnis konfrontiert, das
    genau sie verletzt. Ohne diese Tests waere nur belegt, dass die Muster
    heute stimmen, nicht dass ein kuenftiger Fehlgriff aufgehalten wird.
    """

    ALT = _mit_kopf(
        '  - package-ecosystem: "pip"\n'
        "    labels:\n"
        "      - dependencies\n"
        "    schedule:\n"
        '      interval: "monthly"\n'
    )

    def test_verwaiste_eintraege_werden_beanstandet(self) -> None:
        kaputt = _mit_kopf(
            '  - package-ecosystem: "pip"\n'
            "      - dependencies\n"
            "    schedule:\n"
            '      interval: "monthly"\n'
        )
        grund = edl.pruefe(self.ALT, kaputt)
        self.assertIsNotNone(grund)
        self.assertIn("parst nicht mehr", str(grund))

    def test_stehengebliebenes_labels_wird_beanstandet(self) -> None:
        grund = edl.pruefe(self.ALT, self.ALT)
        self.assertIsNotNone(grund)
        self.assertIn("immer noch", str(grund))

    def test_zuviel_entfernt_wird_beanstandet(self) -> None:
        """Der Schnitt hat `schedule` mitgenommen — parst, kein `labels`, trotzdem falsch."""
        zuviel = _mit_kopf('  - package-ecosystem: "pip"\n')
        grund = edl.pruefe(self.ALT, zuviel)
        self.assertIsNotNone(grund)
        self.assertIn("mehr als", str(grund))

    def test_sauberer_schnitt_wird_durchgelassen(self) -> None:
        """Gegenprobe zu den dreien darueber: `pruefe()` sagt nicht zu allem Nein."""
        sauber = _mit_kopf(
            '  - package-ecosystem: "pip"\n    schedule:\n      interval: "monthly"\n'
        )
        self.assertIsNone(edl.pruefe(self.ALT, sauber))


class ExitCodeTest(unittest.TestCase):
    """Das Wrapper-Skript unterscheidet drei Faelle am Exit-Code.

    Faellt die Unterscheidung zusammen, behandelt der Wrapper einen Fehler wie
    ein «nichts zu tun» und ueberspringt das Repo als erledigt.
    """

    def lauf(self, inhalt: str, *args: str) -> int:
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "dependabot.yml"
            pfad.write_text(inhalt, encoding="utf-8")
            argv = [*args, str(pfad)]
            alt_argv = sys.argv
            sys.argv = ["entferne_dependabot_labels.py", *argv]
            try:
                return edl.main()
            finally:
                sys.argv = alt_argv

    def test_geaendert_ist_null(self) -> None:
        code = self.lauf(_mit_kopf('  - package-ecosystem: "pip"\n    labels: ["x"]\n'))
        self.assertEqual(code, 0)

    def test_nichts_zu_tun_ist_eins(self) -> None:
        code = self.lauf(_mit_kopf('  - package-ecosystem: "pip"\n'))
        self.assertEqual(code, 1)

    def test_unerkanntes_labels_ist_zwei(self) -> None:
        """Ein `labels`, das kein Muster trifft, ist ein Fehler und keine Ruhe.

        Die mehrzeilige Flow-Form trifft absichtlich keines der Muster — sie
        steht hier als Stellvertreter fuer jede Schreibweise, die noch
        auftauchen kann. Meldete das Skript darauf «nichts zu tun», bliebe das
        Repo unbehandelt, ohne dass es jemand erfaehrt.
        """
        code = self.lauf(
            _mit_kopf('  - package-ecosystem: "pip"\n    labels: [\n      "dependencies",\n    ]\n')
        )
        self.assertEqual(code, 2)

    def test_fehlende_datei_ist_zwei(self) -> None:
        alt_argv = sys.argv
        sys.argv = ["entferne_dependabot_labels.py", "/gibt/es/nicht/dependabot.yml"]
        try:
            self.assertEqual(edl.main(), 2)
        finally:
            sys.argv = alt_argv

    def test_kaputtes_ergebnis_wird_nicht_geschrieben(self) -> None:
        """`pruefe()` muss in `main()` verdrahtet sein, nicht bloss existieren.

        Ohne diesen Test bleibt `PruefungTest` vollstaendig gruen, waehrend
        `main()` die Pruefung gar nicht mehr aufruft — die eigentliche
        Zusicherung «eine kaputte Datei wird nie geschrieben» waere dann
        unbelegt. Nachgemessen: haengt man den Aufruf in `main()` aus, faellt
        genau dieser Test und sonst keiner.

        Der Schnitt wird hier absichtlich zerstoerend gemacht, weil die
        Muster den Fall nicht mehr herstellen. Geprueft wird die Verdrahtung,
        nicht das Muster.
        """
        inhalt = _mit_kopf('  - package-ecosystem: "pip"\n    labels: ["x"]\n')
        kaputt = ("version: 2\nupdates:\n  - [\n", 1)
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "dependabot.yml"
            pfad.write_text(inhalt, encoding="utf-8")
            alt_argv = sys.argv
            sys.argv = ["entferne_dependabot_labels.py", str(pfad)]
            try:
                with mock.patch.object(edl, "entferne_labels", return_value=kaputt):
                    self.assertEqual(edl.main(), 2)
            finally:
                sys.argv = alt_argv
            self.assertEqual(
                pfad.read_text(encoding="utf-8"), inhalt, "kaputtes Ergebnis wurde geschrieben"
            )

    def test_dry_run_schreibt_nicht(self) -> None:
        inhalt = _mit_kopf('  - package-ecosystem: "pip"\n    labels: ["x"]\n')
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "dependabot.yml"
            pfad.write_text(inhalt, encoding="utf-8")
            alt_argv = sys.argv
            sys.argv = ["entferne_dependabot_labels.py", "--dry-run", str(pfad)]
            try:
                self.assertEqual(edl.main(), 0)
            finally:
                sys.argv = alt_argv
            self.assertEqual(pfad.read_text(encoding="utf-8"), inhalt)


class ZeilenendenTest(unittest.TestCase):
    """Die Datei verliert die `labels:`-Zeilen — und sonst kein einziges Byte.

    `read_text`/`write_text` uebersetzen Zeilenenden per Vorgabe: Einlesen
    macht aus `\\r\\n` ein `\\n`, Schreiben macht daraus wieder `os.linesep`.
    Auf Windows kommt eine LF-Datei damit als CRLF zurueck, auf Linux
    umgekehrt. Beides macht aus «drei Zeilen entfernt» ein «ganze Datei
    geaendert», und der Lauf ueber das Portfolio wuerde vierzig solche Diffs
    erzeugen, ohne dass ein Gate anschlaegt.

    Geprueft wird deshalb byteweise und in beide Richtungen — eine
    CRLF-Datei bleibt CRLF, eine LF-Datei bleibt LF.

    Was diese Tests belegen und was nicht, gehoert dazu. Rot wird hier nur
    die Lese-Richtung: Nimmt man die byteweise Eingabe wieder heraus, fallen
    die beiden CRLF-Tests. `test_lf_bleibt_lf` dagegen geht auf Linux auch
    ohne jede Korrektur durch, weil `os.linesep` dort `\\n` ist — er kann die
    Windows-Richtung nicht widerlegen, sondern haelt sie nur fest.

    Dass die Schreib-Richtung trotzdem sicher ist, traegt nicht dieser Test,
    sondern die Bauweise: `write_bytes` uebersetzt auf keinem Betriebssystem
    etwas. Eine Zusicherung, die auf der Testmaschine gar nicht falsch werden
    kann, ist eben keine — hier ersetzt sie ein Verfahren, das die Frage nicht
    mehr stellt.
    """

    RUMPF = (
        b"# Kopf, der stehen bleiben muss\n"
        b"version: 2\n"
        b"updates:\n"
        b'  - package-ecosystem: "pip"\n'
        b'    labels: ["dependencies"]\n'
        b"    schedule:\n"
        b'      interval: "monthly"\n'
    )
    ERWARTET = (
        b"# Kopf, der stehen bleiben muss\n"
        b"version: 2\n"
        b"updates:\n"
        b'  - package-ecosystem: "pip"\n'
        b"    schedule:\n"
        b'      interval: "monthly"\n'
    )

    def lauf_auf_bytes(self, roh: bytes) -> bytes:
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "dependabot.yml"
            pfad.write_bytes(roh)
            alt_argv = sys.argv
            sys.argv = ["entferne_dependabot_labels.py", str(pfad)]
            try:
                self.assertEqual(edl.main(), 0)
            finally:
                sys.argv = alt_argv
            return pfad.read_bytes()

    def test_crlf_bleibt_crlf(self) -> None:
        ergebnis = self.lauf_auf_bytes(self.RUMPF.replace(b"\n", b"\r\n"))
        self.assertEqual(ergebnis, self.ERWARTET.replace(b"\n", b"\r\n"))

    def test_lf_bleibt_lf(self) -> None:
        self.assertEqual(self.lauf_auf_bytes(self.RUMPF), self.ERWARTET)

    def test_crlf_im_blockform(self) -> None:
        """Auch die Blockform: der Schnitt darf nicht am `\\r` vorbeigreifen.

        Ohne `rstrip("\\r\\n")` endet die Schluesselzeile auf `labels:\\r`.
        `_LABELS_BLOCK` traefe sie zwar noch, weil `\\s*` das `\\r` frisst —
        aber darauf soll sich niemand verlassen muessen, und die Listenzeilen
        haengen an derselben Frage.
        """
        roh = (
            b"version: 2\n"
            b"updates:\n"
            b'  - package-ecosystem: "pip"\n'
            b"    labels:\n"
            b"      - dependencies\n"
            b"      - python\n"
            b"    schedule:\n"
            b'      interval: "monthly"\n'
        ).replace(b"\n", b"\r\n")
        erwartet = (
            b"version: 2\n"
            b"updates:\n"
            b'  - package-ecosystem: "pip"\n'
            b"    schedule:\n"
            b'      interval: "monthly"\n'
        ).replace(b"\n", b"\r\n")
        self.assertEqual(self.lauf_auf_bytes(roh), erwartet)


if __name__ == "__main__":
    unittest.main()
