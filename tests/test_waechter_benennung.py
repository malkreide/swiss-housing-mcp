"""Der Wächter heisst in der CI und in der Anleitung gleich.

Das Issue-Präfix in `ci.yml` ist die Dedup-Kupplung: Ein zweiter roter Lauf
erkennt das offene Issue am Titelanfang und hängt sich an, statt ein zweites
aufzumachen. `CONTRIBUTING.md` und `CONTRIBUTING.de.md` nennen dasselbe Präfix,
damit jemand das Issue auch von Hand findet.

Am 18.9.2026 wurde das Präfix umbenannt und beide Anleitungen blieben stehen —
sie nannten weiter `public.madd.bfs.admin.ch`, also ausgerechnet die Quelle, die
der alte Name falsch herausgegriffen hatte. Wer danach suchte, fand nichts und
hielt das für «kein Issue offen». Aufgefallen ist es in einem Codex-Review,
nicht beim Schreiben.

Der Rückfall ist still: Kein Gate wird rot, die Automatik dedupliziert weiter
korrekt. Nur der Mensch sucht am falschen Titel.
"""

from __future__ import annotations

import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_CI = _ROOT / ".github" / "workflows" / "ci.yml"
_ANLEITUNGEN = (_ROOT / "CONTRIBUTING.md", _ROOT / "CONTRIBUTING.de.md")

# Die Zuweisung im Workflow-Skript, nicht der Titel im Issue-Body: Dort steht
# das Präfix mit angehängtem Datum und taugt nicht als Anker.
_PREFIX = re.compile(r"""const\s+PREFIX\s*=\s*['"]([^'"]+)['"]""")


def _praefix_aus_der_ci() -> str:
    treffer = _PREFIX.findall(_CI.read_text(encoding="utf-8"))
    assert len(treffer) == 1, (
        f"in {_CI.name} steht das Issue-Präfix nicht genau einmal, sondern "
        f"{len(treffer)}-mal: {treffer}. Mehrere Quellen driften auseinander"
    )
    return treffer[0]


def test_der_praefix_leser_findet_ueberhaupt_etwas() -> None:
    """Positivkontrolle.

    Ohne sie bestuenden die Tests unten auch dann, wenn die Zuweisung
    umformuliert wuerde und der Ausdruck ins Leere liefe — ein Gate, das nichts
    mehr liest, ist gruen und wertlos.
    """
    praefix = _praefix_aus_der_ci()
    assert praefix.strip(), "leeres Praefix aus der CI gelesen"
    assert len(praefix) > 10, f"verdaechtig kurzes Praefix: {praefix!r}"


def test_beide_anleitungen_nennen_das_praefix_der_ci() -> None:
    praefix = _praefix_aus_der_ci()
    fehlend = [p.name for p in _ANLEITUNGEN if praefix not in p.read_text(encoding="utf-8")]
    assert not fehlend, (
        f"{fehlend} nennen das Issue-Praefix der CI nicht mehr: {praefix!r}. "
        "Wer dem Text folgt, sucht ein Issue, das unter diesem Titel nie "
        "angelegt wird"
    )


def test_keine_anleitung_nennt_ein_veraltetes_praefix() -> None:
    """Die Gegenrichtung.

    Der Test darueber bestuende auch, wenn neben dem richtigen Praefix noch das
    alte im Text stuende — und genau das ist die wahrscheinlichere Haelfte des
    Fehlers beim Umbenennen: einen Vorkommen nachziehen, den zweiten vergessen.
    """
    praefix = _praefix_aus_der_ci()
    veraltet = {}
    for p in _ANLEITUNGEN:
        for nr, zeile in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "Live-Tests gegen" in zeile and praefix not in zeile:
                veraltet[f"{p.name}:{nr}"] = zeile.strip()
    assert not veraltet, (
        f"veraltete Wächter-Titel neben dem geltenden Praefix {praefix!r}: {veraltet}"
    )
