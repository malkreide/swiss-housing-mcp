"""Die Bedienungsanleitung muss die Werkzeuge wahrheitsgemaess beschreiben.

Anlass ist ein P2-Befund von Codex auf PR #55, und er traf genau ins Schwarze.
Die `instructions` fassten fuenf Werkzeuge als «die statistischen Tools»
zusammen und gaben eine einzige Kanton-Regel dazu: «pass `canton` explicitly
when a BFS number cannot be resolved». Die Regel stimmt fuer drei von ihnen.

Die anderen loesen naemlich gar nichts auf. `lookup_dwellings`,
`buildings_in_bbox` und `explain_code` haben `canton: str = "zh"` — wer der
alten Anleitung folgte und `canton` wegliess, befragte fuer einen EGID aus dem
Aargau den Zuercher Dump. Der antwortet nicht mit einem Fehler, sondern mit
nichts. Das ist dieselbe Klasse wie der stille Fehlbefund, gegen den
`dump_status` im Server ueberhaupt existiert.

Warum ein Test und nicht bloss der korrigierte Satz: Prosa verrottet
geraeuschlos. Ein Werkzeug, das spaeter mit `canton: str = "zh"` dazukommt und
in der Anleitung nicht auftaucht, faellt sonst niemandem auf — die Anleitung
wuerde dann wieder das Falsche behaupten, und zwar fuer ein Werkzeug, das es
beim Schreiben des Satzes noch gar nicht gab.

Die Gruppen sind deshalb NICHT hier aufgezaehlt, sondern aus dem
Werkzeug-Schema abgeleitet, das der Client tatsaechlich sieht:

* `canton` mit `default: "zh"` — ein konkreter Vorgabewert, also keine
  Aufloesung; das Werkzeug gehoert in die Ausdruecklich-Gruppe.
* `canton` mit `default: null` — der Server loest den Kanton aus der
  BFS-Nummer auf.

Eine Liste im Test waere eine zweite Kopie, die mit derselben Berechtigung
driftet wie der Prosatext, den sie sichern soll.
"""

from __future__ import annotations

import ast
import pathlib

import pytest
from mcp import Client

from swiss_housing_mcp.server import mcp

SERVER_PY = pathlib.Path(__file__).resolve().parents[1] / "src" / "swiss_housing_mcp" / "server.py"

# Ankersaetze der beiden Absaetze. Bewusst kurze, inhaltstragende Fragmente:
# ein ganzer Satz als Anker bricht bei jeder Umformulierung, ein einzelnes Wort
# trifft auch den falschen Absatz.
ANKER_AUSDRUECKLICH = "ALWAYS pass `canton`"
ANKER_AUFLOESEND = "resolve the canton themselves"
ANKER_DUMP = "read a cantonal dump"
ANKER_AUSNAHME = "is NOT one of them"


def dump_gestuetzte_werkzeuge() -> set[str]:
    """Werkzeuge, die tatsaechlich einen Dump holen — aus dem Quelltext.

    Ueber `ast` und nicht ueber `inspect.getsource`: welche Objekte der
    `@mcp.tool`-Dekorator zurueckgibt, ist Sache des SDK und kann sich mit
    einem Bump aendern. Der Quelltext kann das nicht.

    Kriterium ist der Aufruf von `store.ensure_dump` im Rumpf. Das ist die
    einzige Stelle, an der ein Dump geholt wird; ein Werkzeug ohne diesen
    Aufruf kontaktiert die Quelle nicht.
    """
    baum = ast.parse(SERVER_PY.read_text(encoding="utf-8"))
    namen = set()
    for knoten in baum.body:
        if not isinstance(knoten, ast.AsyncFunctionDef):
            continue
        if not any(
            isinstance(d, ast.Call) and getattr(d.func, "attr", None) == "tool"
            for d in knoten.decorator_list
        ):
            continue
        if any(isinstance(k, ast.Attribute) and k.attr == "ensure_dump" for k in ast.walk(knoten)):
            namen.add(knoten.name)
    return namen


def alle_werkzeugnamen() -> set[str]:
    baum = ast.parse(SERVER_PY.read_text(encoding="utf-8"))
    return {
        k.name
        for k in baum.body
        if isinstance(k, ast.AsyncFunctionDef)
        and any(
            isinstance(d, ast.Call) and getattr(d.func, "attr", None) == "tool"
            for d in k.decorator_list
        )
    }


async def werkzeug_gruppen() -> tuple[set[str], set[str]]:
    """(Werkzeuge mit stiller `zh`-Vorgabe, Werkzeuge mit BFS-Aufloesung)."""
    async with Client(mcp) as client:
        tools = (await client.list_tools()).tools

    still, aufloesend = set(), set()
    for tool in tools:
        schema = (tool.input_schema or {}).get("properties", {}).get("canton")
        if schema is None:
            continue
        # `default` fehlt = Pflichtparameter; dann ist nichts still.
        if "default" not in schema:
            continue
        if schema["default"] is None:
            aufloesend.add(tool.name)
        else:
            still.add(tool.name)
    return still, aufloesend


def absatz(text: str, anker: str) -> str:
    """Der Aufzaehlungspunkt, der `anker` enthaelt."""
    for zeile in text.split("\n"):
        if anker in zeile:
            return zeile
    raise AssertionError(f"kein Absatz mit «{anker}» in den instructions")


async def test_jedes_werkzeug_mit_stiller_zh_vorgabe_wird_benannt() -> None:
    """Der Befund selbst, als Zusicherung.

    Faellt dieser Test, ist ein Werkzeug mit `canton: str = "zh"` dazugekommen,
    das die Anleitung nicht nennt — ein Aufrufer ausserhalb Zuerichs bekaeme
    dafuer stillschweigend den Zuercher Dump.
    """
    still, _ = await werkzeug_gruppen()
    assert still, "keine Werkzeuge mit konkreter canton-Vorgabe gefunden — Ableitung kaputt?"

    zeile = absatz(mcp.instructions or "", ANKER_AUSDRUECKLICH)
    fehlend = sorted(name for name in still if f"`{name}`" not in zeile)
    assert not fehlend, (
        f"{fehlend} hat/haben `canton` mit fester Vorgabe, wird/werden aber nicht "
        "in der Ausdruecklich-Regel genannt. Ohne diese Nennung folgt ein Aufrufer "
        "der Regel fuer die aufloesenden Werkzeuge und befragt den falschen Dump."
    )


async def test_jedes_aufloesende_werkzeug_steht_in_der_anderen_gruppe() -> None:
    """Die Gegenrichtung: sonst koennte ein Satz alle Werkzeuge nennen und bestehen."""
    _, aufloesend = await werkzeug_gruppen()
    assert aufloesend

    zeile = absatz(mcp.instructions or "", ANKER_AUFLOESEND)
    fehlend = sorted(name for name in aufloesend if f"`{name}`" not in zeile)
    assert not fehlend, f"{fehlend} loest/loesen die BFS-Nummer auf, steht/stehen aber nicht dort"


async def test_kein_werkzeug_steht_in_beiden_gruppen() -> None:
    """Haelt die Trennung scharf.

    Ohne diese Zusicherung koennte man beide Tests oben befriedigen, indem man
    schlicht alle neun Namen in beide Absaetze schreibt — die Anleitung waere
    dann wieder so unspezifisch wie die, die den Befund ausgeloest hat.
    """
    still, aufloesend = await werkzeug_gruppen()
    text = mcp.instructions or ""
    a, b = absatz(text, ANKER_AUSDRUECKLICH), absatz(text, ANKER_AUFLOESEND)

    for name in still:
        assert f"`{name}`" not in b, f"{name} steht auch bei den aufloesenden Werkzeugen"
    for name in aufloesend:
        assert f"`{name}`" not in a, f"{name} steht auch bei den stillen Werkzeugen"


async def test_die_regel_sagt_was_schiefgeht_nicht_nur_was_zu_tun_ist() -> None:
    """Eine Anweisung ohne Folge wird wegoptimiert.

    Ein Modell, das nur «pass `canton`» liest, laesst den Parameter unter
    Kontextdruck weg. Dass die Quelle bei falschem Kanton *nichts* liefert statt
    zu scheitern, ist der Grund, warum die Regel nicht optional ist — und
    gehoert deshalb in den Text.
    """
    text = (mcp.instructions or "").lower()
    assert "empty or wrong" in text or "finds nothing" in text, (
        "die Kanton-Regel nennt keine Folge; ohne sie liest sie sich wie eine Stilfrage"
    )


@pytest.mark.parametrize("anker", [ANKER_AUSDRUECKLICH, ANKER_AUFLOESEND])
def test_die_anker_existieren(anker) -> None:
    """Sagt es geradeheraus, wenn eine Umformulierung die Anker entfernt hat.

    Ohne diesen Test schluege eine Umbenennung als `AssertionError` aus
    `absatz()` durch — richtig, aber an vier Stellen und ohne den Hinweis,
    dass nur der Anker nachzuziehen ist.
    """
    assert anker in (mcp.instructions or ""), (
        f"Anker «{anker}» fehlt — wurde der Absatz umformuliert? Dann hier nachziehen."
    )


async def test_jedes_dump_gestuetzte_werkzeug_wird_benannt() -> None:
    """P2-Befund von Codex auf PR #56, zweiter Teil.

    Hier stand «The remaining tools read a cantonal dump» — eine Formel, die
    kein einziges Werkzeug nennt und deshalb auch `dump_status` einschloss.
    Das ist nicht bloss ungenau: `dump_status` ist der Einstieg, wenn die
    Quelle ausgefallen scheint, und die Formel liess einen Client annehmen, es
    wuerde dabei dieselbe Quelle kontaktieren. Genau dann haette er es gemieden.
    """
    dump = dump_gestuetzte_werkzeuge()
    assert dump, "kein Werkzeug ruft ensure_dump — Ableitung kaputt?"

    zeile = absatz(mcp.instructions or "", ANKER_DUMP)
    fehlend = sorted(name for name in dump if f"`{name}`" not in zeile)
    assert not fehlend, f"{fehlend} holt/holen einen Dump, wird/werden aber nicht genannt"


async def test_kein_dumploses_werkzeug_wird_als_dump_gestuetzt_ausgegeben() -> None:
    """Die Gegenrichtung — und der eigentliche Befund.

    Ein Werkzeug ohne `ensure_dump` darf im Dump-Absatz nur vorkommen, um
    ausgenommen zu werden. Die Ausnahme muss also VOR der Nennung stehen.
    """
    ohne_dump = alle_werkzeugnamen() - dump_gestuetzte_werkzeuge()
    assert ohne_dump, "alle Werkzeuge holen Dumps? dann ist die Ableitung kaputt"

    zeile = absatz(mcp.instructions or "", ANKER_DUMP)
    ausnahme = zeile.find(ANKER_AUSNAHME)
    assert ausnahme != -1, f"kein «{ANKER_AUSNAHME}» im Dump-Absatz"

    for name in ohne_dump:
        stelle = zeile.find(f"`{name}`")
        if stelle == -1:
            continue
        assert stelle >= ausnahme - len(f"`{name}` "), (
            f"{name} holt keinen Dump, steht aber vor der Ausnahme — ein Client "
            "liest es als dump-gestuetzt und meidet es bei einer Stoerung"
        )


def test_die_aufloesung_nennt_ihre_grenze() -> None:
    """P2-Befund von Codex auf PR #56, erster Teil.

    `_canton_for_municipality` durchsucht nur bereits gecachte Dumps und faellt
    dann auf einen Seed zurueck, der genau BFS 261 kennt. Auf kaltem Cache
    scheitert sie also fuer jede andere Gemeinde, ohne irgendetwas zu laden.

    Hier stand «Pass `canton` only if that resolution fails» — das schickte
    jeden Aufrufer ausserhalb Zuerichs zuerst in einen garantiert vergeblichen
    Aufruf. Die Grenze gehoert genannt, sonst liest sich die Regel als
    «Aufloesung klappt normalerweise».
    """
    zeile = absatz(mcp.instructions or "", ANKER_AUFLOESEND)
    assert "already cached" in zeile, (
        "die Aufloesung wird ohne ihre Grenze beschrieben; ein Aufrufer verlaesst "
        "sich dann darauf und zahlt einen vergeblichen Rundlauf"
    )
    assert "261" in zeile, "der einzige vom Seed gedeckte BFS-Wert wird nicht genannt"

    # Zweiter P2-Befund auf demselben PR, nachgereicht am 18.9.2026: Hier stand
    # «cached in this process». Der Cache ist aber ein Verzeichnis —
    # `GwrStore.status()` prueft `path.exists()`, und `_canton_for_municipality`
    # laeuft genau ueber dessen Ergebnis. Nach einem Neustart zaehlt jede
    # vorhandene Datei weiter als gecacht. Wer «in this process» las, hielt eine
    # Abfrage fuer aussichtslos, die durchgelaufen waere.
    assert "in this process" not in zeile, (
        "die Aufloesung wird als Prozess-Zustand beschrieben; sie liest aber ein "
        "Verzeichnis und ueberlebt einen Neustart"
    )
    assert "disk" in zeile, "die Dauerhaftigkeit des Caches wird nicht benannt"
