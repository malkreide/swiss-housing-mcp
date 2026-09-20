"""Jede Action in den Workflows haengt an einem Commit, nicht an einem Namen.

`actions/checkout@v7` ist kein Zustand, sondern ein Zeiger: Wer das Tag
verschiebt, aendert damit, was in diesem Repo laeuft — ohne Commit hier, ohne
Review, ohne dass ein Gate rot wird. Bei `live` haengt daran ein Schritt mit
`issues: write`, bei `publish.yml` der Weg, ueber den das PyPI-Token laeuft.

Der Rueckfall ist still und wahrscheinlich: `@v7` liest sich richtig, ist
kuerzer und steht in jedem Beispiel im Netz. Dependabot pflegt SHA-Pins
mitsamt Versionskommentar weiter, dieser Test streitet also nicht mit ihm —
er faengt die Hand, die beim naechsten neuen Schritt `@v4` tippt.

ACHTUNG beim Aufloesen eines Tags: Ist es ein *annotiertes* Tag, nennt
`git ls-remote` das Tag-Objekt und nicht den Commit. Zweimal getroffen —
`pypa/gh-action-pypi-publish` v1.14.2 (Tag `a892a5a6…`, Commit `dc37677b…`)
und `actions/github-script` v9.0.0 (Tag `d746ffe3…`, Commit `3a2844b7…`).
Ein Tag-Objekt als `uses:`-Ref laeuft nicht; die Zeile sieht aber gepinnt aus
und dieser Test haelt sie fuer gueltig. Immer `refs/tags/<tag>^{}` mitabfragen
und den Commit nehmen, wenn eine zweite Zeile kommt.
"""

from __future__ import annotations

import pathlib
import re

import pytest
import yaml

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOWS = sorted((_ROOT / ".github" / "workflows").glob("*.yml"))

# Die Rohzeile, nicht der geparste Baum: Der Versionskommentar ist YAML-
# Kommentar und ueberlebt `safe_load` nicht. Geprueft wird beides, und die
# Zaehlung unten haelt die zwei Lesarten gegeneinander.
_USES = re.compile(r"^\s*(?:-\s*)?uses:\s*(\S+)\s*(?:#\s*(\S+))?\s*$")
_SHA = re.compile(r"^[0-9a-f]{40}$")
_VERSIONSKOMMENTAR = re.compile(r"^v[0-9]")


def _zeilen_mit_uses(text: str) -> list[tuple[int, str, str | None]]:
    """(Zeilennummer, Ref hinter dem `@`, Kommentar) je `uses:`-Zeile."""
    gefunden = []
    for nr, zeile in enumerate(text.splitlines(), 1):
        treffer = _USES.match(zeile)
        if treffer is None:
            continue
        verweis, kommentar = treffer.group(1), treffer.group(2)
        _, _, ref = verweis.partition("@")
        gefunden.append((nr, ref, kommentar))
    return gefunden


def _uses_laut_yaml(text: str) -> int:
    baum = yaml.safe_load(text)
    return sum(
        1 for job in baum["jobs"].values() for schritt in job.get("steps", []) if "uses" in schritt
    )


def test_es_gibt_ueberhaupt_workflows() -> None:
    """Positivkontrolle fuer den Dateifund.

    Ohne sie liefen alle Tests unten gruen durch, sobald das Verzeichnis
    umzieht oder die Dateien auf `.yaml` enden — ein Gate ueber einer leeren
    Liste prueft nichts.
    """
    assert _WORKFLOWS, f"keine Workflows unter {_ROOT / '.github' / 'workflows'} gefunden"


@pytest.mark.parametrize("pfad", _WORKFLOWS, ids=lambda p: p.name)
def test_der_zeilenleser_sieht_dasselbe_wie_der_yaml_parser(pfad: pathlib.Path) -> None:
    """Positivkontrolle fuer den Ausdruck.

    Genau die Falle aus `test_waechter_benennung.py`: Wird die Schreibweise
    der `uses:`-Zeilen umgestellt, laeuft der Ausdruck ins Leere und meldet
    keinen Verstoss mehr. Der YAML-Parser kennt die Kommentare nicht, zaehlt
    die Schritte aber unabhaengig — stimmen beide Zahlen nicht ueberein, liest
    einer von beiden falsch.
    """
    text = pfad.read_text(encoding="utf-8")
    per_zeile = len(_zeilen_mit_uses(text))
    per_yaml = _uses_laut_yaml(text)
    assert per_zeile == per_yaml, (
        f"{pfad.name}: der Zeilenausdruck findet {per_zeile} `uses:`, der "
        f"YAML-Parser {per_yaml}. Einer der beiden liest an der Datei vorbei"
    )
    assert per_zeile > 0, f"{pfad.name} hat keine `uses:`-Zeile — pruefen, ob das stimmt"


@pytest.mark.parametrize("pfad", _WORKFLOWS, ids=lambda p: p.name)
def test_jede_action_haengt_an_einem_commit(pfad: pathlib.Path) -> None:
    ungepinnt = {
        f"{pfad.name}:{nr}": ref
        for nr, ref, _ in _zeilen_mit_uses(pfad.read_text(encoding="utf-8"))
        if not _SHA.match(ref)
    }
    assert not ungepinnt, (
        f"Actions an einem verschiebbaren Ref statt an einem Commit: {ungepinnt}. "
        "Wer das Tag drueben verschiebt, aendert damit, was hier laeuft. "
        "Aufloesen mit `git ls-remote <url> refs/tags/<tag> 'refs/tags/<tag>^{}'` "
        "und den Commit aus der zweiten Zeile nehmen, falls eine kommt"
    )


@pytest.mark.parametrize("pfad", _WORKFLOWS, ids=lambda p: p.name)
def test_jeder_pin_nennt_seine_version(pfad: pathlib.Path) -> None:
    """Die andere Haelfte.

    Ein nackter SHA ist sicher und unlesbar: Niemand sieht ihm an, ob er zwei
    Wochen oder drei Jahre alt ist, und bei einem Sicherheitshinweis zu einer
    Version laesst er sich nicht zuordnen. Dependabot schreibt den Kommentar
    beim Bump mit — faellt er weg, ist die Zeile von Hand gesetzt worden.
    """
    ohne = {
        f"{pfad.name}:{nr}": ref
        for nr, ref, kommentar in _zeilen_mit_uses(pfad.read_text(encoding="utf-8"))
        if kommentar is None or not _VERSIONSKOMMENTAR.match(kommentar)
    }
    assert not ohne, (
        f"SHA-Pins ohne Versionskommentar `# vX.Y.Z`: {ohne}. Der SHA allein "
        "sagt nicht, welche Version dort haengt"
    )


# Gegenprobe. Die Tests oben bestuenden auch, wenn `_SHA` oder
# `_VERSIONSKOMMENTAR` jede Eingabe durchliessen — dieser Satz zeigt, dass sie
# genau bei den falschen Formen fallen.
_PROBEN = [
    ("      - uses: actions/checkout@v7", False, "Major-Tag"),
    ("      - uses: actions/checkout@v7.0.1", False, "Patch-Tag"),
    ("      - uses: actions/checkout@main", False, "Branch"),
    ("      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba", False, "SHA zu kurz"),
    (
        "      - uses: actions/checkout@3D3C42E5AAC5BA805825DA76410C181273BA90B1",
        False,
        "Grossbuchstaben",
    ),
    (
        "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        True,
        "nackter SHA",
    ),
    (
        "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1",
        True,
        "SHA mit Version",
    ),
]


@pytest.mark.parametrize("zeile, gepinnt, was", _PROBEN, ids=[p[2] for p in _PROBEN])
def test_gegenprobe_der_pin_erkennung(zeile: str, gepinnt: bool, was: str) -> None:
    gefunden = _zeilen_mit_uses(zeile)
    assert len(gefunden) == 1, f"{was}: Zeile gar nicht als `uses:` erkannt"
    _, ref, _ = gefunden[0]
    assert bool(_SHA.match(ref)) is gepinnt, f"{was}: {ref!r} falsch eingeordnet"


def test_gegenprobe_der_kommentar_erkennung() -> None:
    nackt = "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
    mit = nackt + " # v7.0.1"
    assert _zeilen_mit_uses(nackt)[0][2] is None, "fehlender Kommentar nicht bemerkt"
    assert _zeilen_mit_uses(mit)[0][2] == "v7.0.1", "Kommentar nicht gelesen"
