"""Die ruff-Version steht an genau einer Stelle — und bleibt dort.

Sie stand an zweien: `ruff>=0.5` im `[dev]`-Extra und
`pip install ruff==0.16.1` in `ci.yml`. Der CI-Schritt lief nach dem Install
des Extras und gewann gegen pyproject — der Wert dort war wirkungslos, und wer
die Gates lokal fuhr, benutzte die jeweils neueste Version statt der, gegen die
die CI prueft.

Beide Rueckfaelle sind still: Sie machen kein Gate rot, sie lassen es lediglich
mit einer anderen Version laufen als der, gegen die lokal geprueft wurde.
"""

from __future__ import annotations

import pathlib
import re
import tomllib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOWS = _ROOT / ".github" / "workflows"
_CLAUDE_MD = _ROOT / "CLAUDE.md"

# Die Pin-Form, und nur sie. Eine Jahreszahl oder ein erzaehltes «der Bump auf
# 0.16.1» ist Geschichte und darf stehen bleiben; `ruff==X.Y.Z` behauptet
# dagegen einen geltenden Pin und ist damit eine zweite Quelle.
#
# Gross-/Kleinschreibung und Leerraum um `==` gehoeren dazu: `Ruff==0.17.0` und
# `ruff == 0.17.0` sind beide gueltige Requirement-Schreibweisen (PEP 508 laesst
# Leerraum zu, und Paketnamen vergleicht pip normalisiert), veralten also nach
# einem Bump genauso. Die erste Fassung kannte nur exakt `ruff==` und liess
# beide durch — aufgefallen in einem Codex-Review, nicht beim Schreiben.
_RUFF_PIN = re.compile(r"(?i)(?<![\w.-])ruff\s*==\s*\d+\.\d+\.\d+")

# Formen, in denen ein Schritt ein Paket eigenstaendig installiert. Die erste
# Fassung dieses Tests kannte nur `pip install ruff` und liess damit
# `pip install --upgrade ruff==…`, `pip install "ruff==…"`, `pip3 install`,
# `uv tool install` und `uv run --with ruff==…` durch — allesamt Formen, die
# den Pin genauso ueberstimmen. Aufgefallen ist das in einem Codex-Review.
_INSTALL_FORM = re.compile(
    r"(?:pip3?\s+install|python\s+-m\s+pip\s+install|uv\s+pip\s+install"
    r"|uv\s+tool\s+install|uv\s+add|pipx\s+install|--with)\b"
)
# ruff als eigenes Paket-Argument. Anfuehrungszeichen sind erlaubt, ein
# vorangehendes Wort-, Pfad- oder Bindestrich-Zeichen nicht: sonst zaehlten
# `ruff-lsp` und `scripts/ruff_helper.py` mit.
_RUFF_PAKET = re.compile(r"""(?<![\w./-])["']?ruff(?![\w-])""")


def _installiert_ruff(zeile: str) -> bool:
    """Installiert diese Zeile ruff als benanntes Paket?

    `pip install -e ".[dev]"` zieht ruff ebenfalls herein — das ist aber der
    richtige Weg und darf nicht anschlagen. Entscheidend ist deshalb, ob nach
    dem Install-Befehl ein eigenes Argument `ruff` steht.
    """
    treffer = _INSTALL_FORM.search(zeile)
    return bool(treffer) and bool(_RUFF_PAKET.search(zeile[treffer.end() :]))


def _workflow_dateien() -> list[pathlib.Path]:
    """Beide Endungen: GitHub laedt `*.yml` UND `*.yaml`."""
    return sorted([*_WORKFLOWS.glob("*.yml"), *_WORKFLOWS.glob("*.yaml")])


def _dev_abhaengigkeiten() -> list[str]:
    daten = tomllib.loads((_ROOT / "pyproject.toml").read_text())
    return daten["project"]["optional-dependencies"]["dev"]


def test_ruff_ist_exakt_gepinnt() -> None:
    """Eine Spanne laesst lokalen Lauf und CI verschiedene Versionen fahren."""
    specs = [s for s in _dev_abhaengigkeiten() if re.match(r"^ruff\b", s)]
    assert len(specs) == 1, f"genau ein ruff-Specifier erwartet, gefunden: {specs}"
    assert re.fullmatch(r"ruff==\d+\.\d+\.\d+", specs[0]), (
        f"ruff muss als ruff==X.Y.Z gepinnt sein, gefunden {specs[0]!r}."
    )


def test_der_pin_ist_die_einzige_versionsquelle() -> None:
    """Kein Workflow darf ruff selbst installieren."""
    for workflow in _workflow_dateien():
        zeilen = [z for z in workflow.read_text().splitlines() if not z.lstrip().startswith("#")]
        treffer = [z.strip() for z in zeilen if _installiert_ruff(z)]
        assert not treffer, (
            f"{workflow.name} installiert ruff direkt ({treffer}). Dieser Schritt "
            "laeuft nach dem dev-Install und ueberstimmt den Pin in pyproject."
        )


def test_der_workflow_scan_findet_ueberhaupt_etwas() -> None:
    """Sichert die Pruefung oben gegen ein leeres Verzeichnis ab."""
    workflows = _workflow_dateien()
    assert len(workflows) >= 2, f"Workflow-Scan findet fast nichts: {workflows}"
    assert any("ruff check" in w.read_text() for w in workflows), (
        "kein Workflow ruft ruff auf — der Scan sucht am falschen Ort"
    )


def test_der_erkenner_kennt_die_gaengigen_installationsformen() -> None:
    """Der Scan ist nur so gut wie das, was er als Install erkennt.

    Ohne diese Tabelle ist die Zusicherung oben gruen, weil sie die Form nicht
    kennt — nicht, weil sie fehlt. Genau so war es: Die erste Fassung suchte
    woertlich nach `pip install ruff` und uebersah fuenf von sieben geprueften
    Schreibweisen.
    """
    muss_treffen = [
        "run: pip install ruff==0.16.1",
        "run: pip install --upgrade ruff==0.16.1",
        'run: pip install "ruff==0.16.1"',
        "run: pip install 'ruff==0.16.1'",
        "run: pip3 install ruff==0.16.1",
        "run: python -m pip install ruff==0.16.1",
        "run: uv pip install ruff==0.16.1 --system",
        "run: uv tool install ruff==0.16.1",
        "run: uv add ruff==0.16.1",
        "run: pipx install ruff==0.16.1",
        "run: uv run --with ruff==0.16.1 ruff check src/",
        "run: pip install ruff",
        "run: pip install pytest ruff==0.16.1",
        "run: pip install ruff[extra]==0.16.1",
    ]
    darf_nicht_treffen = [
        'run: pip install -e ".[dev]"',
        'run: uv pip install -e ".[dev]" --system',
        "run: ruff check src/ tests/ scripts/",
        "run: ruff format --check src/ tests/",
        "run: pip install ruff-lsp",
        "run: pip install uv",
        "run: python -m pip install --upgrade pip",
        "run: pip install build hatchling",
        "run: uv run --with pip-audit pip-audit",
        "run: python scripts/ruff_helper.py",
        "run: pip install -r requirements.txt",
        "name: Lint mit ruff",
    ]
    uebersehen = [z for z in muss_treffen if not _installiert_ruff(z)]
    assert not uebersehen, f"Erkenner uebersieht: {uebersehen}"
    fehlalarm = [z for z in darf_nicht_treffen if _installiert_ruff(z)]
    assert not fehlalarm, f"Erkenner schlaegt faelschlich an: {fehlalarm}"


def test_kein_ruff_pin_in_der_projektanweisung() -> None:
    """Die dritte Quelle, die es fast unbemerkt gab.

    Die zwei Tests oben halten `pyproject.toml` und die Workflows auseinander.
    `CLAUDE.md` stand ausserhalb beider — und trug den Satz «ruff: genau eine
    Quelle — `ruff==0.16.3`», waehrend der Pin auf 0.16.5 lief. Ein
    Dependabot-Bump zieht pyproject nach, die Projektanweisung nicht.

    Das ist nicht bloss eine schiefe Doku. Teil 1 derselben Datei verlangt, die
    Gates lokal mit der GEPINNTEN Version zu fahren; wer die Zahl von dort nahm,
    installierte die alte und bekam Formatabweichungen, die niemand verursacht
    hat — der Fehler, vor dem die Datei selbst warnt.

    Verboten ist nur die Pin-Form `ruff==X.Y.Z`. Erzaehlte Versionen ohne sie
    («der Bump auf 0.16.1») beschreiben Vergangenes und bleiben erlaubt.
    """
    if not _CLAUDE_MD.is_file():
        # Uebersprungen, nicht bestanden: Diese Datei wird zwischen den Repos
        # kopiert, und ein stilles `return` liesse den Test dort gruen wirken,
        # wo er nichts geprueft hat.
        pytest.skip("kein CLAUDE.md in diesem Repo")

    treffer = sorted(
        {
            f"Zeile {nr}: {zeile.strip()}"
            for nr, zeile in enumerate(_CLAUDE_MD.read_text(encoding="utf-8").splitlines(), 1)
            if _RUFF_PIN.search(zeile)
        }
    )
    assert not treffer, (
        "CLAUDE.md nennt einen ruff-Pin und ist damit eine zweite Versionsquelle, "
        f"die ein Dependabot-Bump nicht nachzieht: {treffer}. Auf den Pin verweisen "
        "statt ihn zu wiederholen — die Zahl steht in pyproject.toml."
    )


@pytest.mark.parametrize(
    ("zeile", "ist_pin"),
    [
        # Muss treffen — alle vier sind gueltige Requirement-Schreibweisen und
        # veralten nach einem Dependabot-Bump gleichermassen.
        ("ruff==0.16.5", True),
        ("Ruff==0.17.0", True),
        ("ruff == 0.17.0", True),
        ("ruff  ==  0.1.2", True),
        # Darf nicht treffen. Die erzaehlte Zahl ist der Grund, warum hier ein
        # Verbot der Pin-Form steht und kein Verbot von Versionszahlen: Ein
        # Gate, das jede Zahl verboete, machte die historischen Passagen der
        # Projektanweisung unschreibbar.
        ("der Bump auf 0.16.1", False),
        ("ruff 0.16.5", False),
        ("ruff>=0.5", False),
        # Fremde Pakete, deren Name auf «ruff» endet oder ihn enthaelt.
        ("pyruff==0.1.0", False),
        ("my-ruff==0.1.0", False),
    ],
)
def test_der_pin_erkenner_kennt_die_schreibweisen(zeile: str, ist_pin: bool) -> None:
    """Gegenprobe zum Ausdruck selbst.

    Die erste Fassung war `ruff==\\d+\\.\\d+\\.\\d+` — exakt kleingeschrieben, ohne
    Leerraum. `Ruff==0.17.0` und `ruff == 0.17.0` liefen damit durch, obwohl
    beide denselben geltenden Pin ausdruecken. Der Fehlbefund waere still
    gewesen: Das Gate bliebe gruen und die zweite Versionsquelle bestehen.

    Die Negativfaelle sind der wichtigere Teil. Ein zu weiter Ausdruck faerbt
    `pyruff==0.1.0` rot und macht das Gate unbrauchbar, lange bevor jemand
    nachsieht, warum.
    """
    assert bool(_RUFF_PIN.search(zeile)) is ist_pin
