"""Jeder externe Endpunkt, gefahren aus einer aufgezeichneten Antwort.

Die handgeschriebenen Stubs im Rest der Suite pruefen die *Fehler*-Pfade — ein
503, ein leeres Trefferfeld, ein unbekanntes EGID —, die sich nicht auf Zuruf
aufzeichnen lassen und als Erfindung in Ordnung sind. Was sie nicht koennen: die
Form einer Erfolgs-Antwort belegen. Sie stimmen mit dem ueberein, was ihr Autor
annahm.

Der GWR-Dump ist der interessante Fall: die Quelle liefert ein ZIP mit einer
SQLite-Datenbank, die der Server per SQL abfragt. Tabellen- und Spaltennamen
sind dort die Satzform — und genau das, was eine erfundene Fixture raten
muesste. Die Aufzeichnung uebernimmt das Schema wortgleich.

Herkunft, Datum, Auswahlregel und SHA-256 je Datei stehen in
`tests/fixtures/PROVENANCE.md`; neu aufzeichnen mit
`python scripts/record_fixtures.py`.
"""

from __future__ import annotations

import datetime as dt
import re
import sqlite3
import zipfile

import httpx
import pytest
import respx
from fixture_data import fixture_bytes, fixture_json, provenance, recorded_names

from swiss_housing_mcp import gwr

# Jeder externe Endpunkt dieses Servers und die Fixture dazu. Ein Endpunkt ohne
# Aufzeichnung faellt in `test_jeder_endpunkt_hat_eine_aufzeichnung`.
ENDPUNKTE = {
    "madd/{kanton}.zip": "gwr_ai.zip",
    "geoadmin/SearchServer": "geoadmin_search.json",
    "geoadmin/MapServer/find": "geoadmin_find_egid.json",
}

KANTON = "ai"


# --------------------------------------------------------------------------
# Herkunft
# --------------------------------------------------------------------------


def test_provenance_nennt_ein_brauchbares_aufnahmedatum():
    """Eine Aufzeichnung ohne Datum ist eine undatierte Behauptung ueber die Quelle."""
    match = re.search(r"Aufgezeichnet am \*\*(\d{4}-\d{2}-\d{2})\*\*", provenance())
    assert match, "PROVENANCE.md nennt kein Aufnahmedatum im erwarteten Format"
    when = dt.date.fromisoformat(match.group(1))
    assert when <= dt.datetime.now(dt.UTC).date(), "Aufnahmedatum liegt in der Zukunft"


def test_jede_fixture_steht_in_der_provenance():
    """Sonst waechst der Ordner und der Nachweis bleibt zurueck."""
    text = provenance()
    fehlend = [n for n in recorded_names() if f"## `{n}`" not in text]
    assert not fehlend, f"ohne Eintrag in PROVENANCE.md: {fehlend}"


def test_jeder_endpunkt_hat_eine_aufzeichnung():
    """Bewacht die Regel selbst: eine aufgezeichnete Antwort je externem Endpunkt."""
    fehlend = sorted(set(ENDPUNKTE.values()) - set(recorded_names()))
    assert not fehlend, f"Endpunkte ohne Aufzeichnung: {fehlend}"


# --------------------------------------------------------------------------
# Der GWR-Dump: ZIP mit SQLite
# --------------------------------------------------------------------------


def test_der_dump_traegt_das_schema_der_quelle():
    """Tabellen und Spalten, nicht nachgebaut sondern uebernommen.

    Benennt das BFS eine Spalte um, faellt dieser Test — und zwar bevor eine
    SQL-Abfrage im Server ins Leere laeuft. Ein erfundenes Schema haette den
    Wechsel per Konstruktion nicht bemerken koennen.
    """
    import io

    with zipfile.ZipFile(io.BytesIO(fixture_bytes("gwr_ai.zip"))) as zf:
        assert zf.namelist() == ["data.sqlite"], "der Server entpackt genau dieses Mitglied"
        rohdaten = zf.read("data.sqlite")

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".sqlite") as tmp:
        tmp.write(rohdaten)
        tmp.flush()
        con = sqlite3.connect(f"file:{tmp.name}?mode=ro", uri=True)
        try:
            tabellen = {
                r[0] for r in con.execute("select name from sqlite_master where type='table'")
            }
            assert {"building", "entrance", "dwelling", "code"} <= tabellen
            spalten = {r[1] for r in con.execute('pragma table_info("building")')}
            # Die Schluessel, auf denen die Abfragen des Servers beruhen.
            assert {"EGID", "GDEKT", "GGDENR", "GGDENAME"} <= spalten
            assert len(spalten) > 40, "die Satzform von `building` ist breit — Auswahl pruefen"
        finally:
            con.close()


def test_der_dump_ist_zusammenhaengend():
    """Ein Gebaeude ohne Eingaenge und Wohnungen belegt die Verknuepfung nicht."""
    import io
    import tempfile

    with zipfile.ZipFile(io.BytesIO(fixture_bytes("gwr_ai.zip"))) as zf:
        rohdaten = zf.read("data.sqlite")
    with tempfile.NamedTemporaryFile(suffix=".sqlite") as tmp:
        tmp.write(rohdaten)
        tmp.flush()
        con = sqlite3.connect(f"file:{tmp.name}?mode=ro", uri=True)
        try:
            egid = con.execute("select EGID from building limit 1").fetchone()[0]
            eingaenge = con.execute(
                "select count(*) from entrance where EGID = ?", (egid,)
            ).fetchone()[0]
            wohnungen = con.execute(
                "select count(*) from dwelling where EGID = ?", (egid,)
            ).fetchone()[0]
            assert eingaenge > 0, "das aufgezeichnete Gebaeude soll Eingaenge haben"
            assert wohnungen > 0, "das aufgezeichnete Gebaeude soll Wohnungen haben"
            assert con.execute("select count(*) from code").fetchone()[0] > 100, (
                "`code` ist die Nachschlagetabelle und gehoert vollstaendig dazu"
            )
        finally:
            con.close()


@respx.mock
async def test_ensure_dump_laedt_und_entpackt_die_aufzeichnung(tmp_path, monkeypatch):
    """Der Weg der Quelle bis in die abfragbare Datenbank, ohne Netz."""
    monkeypatch.setattr(gwr, "CACHE_DIR", tmp_path)
    respx.get(f"{gwr.MADD_BASE}/{KANTON}.zip").mock(
        return_value=httpx.Response(200, content=fixture_bytes("gwr_ai.zip"))
    )
    store = gwr.GwrStore()
    async with httpx.AsyncClient() as http:
        await store.ensure_dump(KANTON, http)
    zeilen = store.query(KANTON, "select EGID, GGDENAME from building")
    assert zeilen, "die entpackte Datenbank liefert Gebaeude"
    assert zeilen[0]["EGID"], "EGID ist der Schluessel, auf dem alles beruht"


# --------------------------------------------------------------------------
# geo.admin
# --------------------------------------------------------------------------


@respx.mock
async def test_geoadmin_suche_aus_der_aufzeichnung():
    payload = fixture_json("geoadmin_search.json")
    respx.get(url__startswith=f"{gwr.GEOADMIN_BASE}/SearchServer").mock(
        return_value=httpx.Response(200, json=payload)
    )
    async with httpx.AsyncClient() as http:
        treffer = await gwr.geoadmin_geocode(http, "Bahnhofstrasse 1 Zuerich", limit=3)
    assert treffer, "die Aufzeichnung liefert Treffer"
    # Die Quelle verschachtelt jeden Treffer unter `attrs` — eine Form, die ein
    # Stub leicht flach geraten haette.
    assert all("attrs" in r for r in payload["results"])


@respx.mock
async def test_geoadmin_find_egid_aus_der_aufzeichnung():
    payload = fixture_json("geoadmin_find_egid.json")
    egid = int(payload["results"][0]["attributes"]["egid"])
    respx.get(url__startswith=f"{gwr.GEOADMIN_BASE}/MapServer/find").mock(
        return_value=httpx.Response(200, json=payload)
    )
    async with httpx.AsyncClient() as http:
        gebaeude = await gwr.geoadmin_find_egid(http, egid)
    assert gebaeude is not None, "ein bekanntes EGID darf nicht None liefern"


def test_dump_und_geoadmin_meinen_dasselbe_gebaeude():
    """Haelt eine Zusicherung ueber beide Quellen fest, die nur eine Aufzeichnung geben kann.

    Der Recorder schlaegt bei geo.admin genau die EGID nach, die er zuvor aus
    dem Dump gewaehlt hat. Zwei erfundene Fixtures haetten hier leicht zwei
    verschiedene Gebaeude gezeigt, ohne dass es jemandem auffiele.
    """
    import io
    import tempfile

    with zipfile.ZipFile(io.BytesIO(fixture_bytes("gwr_ai.zip"))) as zf:
        rohdaten = zf.read("data.sqlite")
    with tempfile.NamedTemporaryFile(suffix=".sqlite") as tmp:
        tmp.write(rohdaten)
        tmp.flush()
        con = sqlite3.connect(f"file:{tmp.name}?mode=ro", uri=True)
        try:
            dump_egid = con.execute("select EGID from building limit 1").fetchone()[0]
        finally:
            con.close()
    payload = fixture_json("geoadmin_find_egid.json")
    geo_egid = int(payload["results"][0]["attributes"]["egid"])
    assert dump_egid == geo_egid, (
        f"Dump zeigt EGID {dump_egid}, geo.admin {geo_egid} — die Aufzeichnungen "
        "sollen dasselbe Gebaeude belegen"
    )


@pytest.mark.parametrize("name", sorted(ENDPUNKTE.values()))
def test_jede_aufzeichnung_ist_nicht_leer(name):
    """Eine leere Aufzeichnung sieht aus wie eine gueltige und prueft nichts."""
    assert fixture_bytes(name), f"{name} ist leer — neu aufzeichnen"


# --------------------------------------------------------------------------
# Der Nachweis, nachgerechnet
# --------------------------------------------------------------------------
@pytest.mark.parametrize("name", sorted(n for n in recorded_names() if n != "PROVENANCE.md"))
def test_die_pruefsumme_im_nachweis_stimmt(name):
    """Eine Pruefsumme, die niemand nachrechnet, ist Zierde.

    Sie steht im Nachweis, um genau einen Fall zu fangen: eine Aufzeichnung,
    die nach dem Lauf von Hand nachgebessert wurde. Eine korrigierte Antwort
    ist wieder eine erfundene — und von aussen ist ihr das nicht anzusehen.
    Ohne diesen Test faengt die Summe nichts.

    Gerechnet wird ueber die Bytes auf der Platte, nicht ueber den Loader:
    genau die hat der Recorder gehasht, und ein Loader, der unterwegs dekodiert
    oder normalisiert, wuerde die Pruefung gegen sich selbst fuehren.
    """
    import hashlib
    import re
    from pathlib import Path

    teile = provenance().split(f"## `{name}`", 1)
    assert len(teile) == 2, f"{name} hat keinen Block in PROVENANCE.md"
    treffer = re.search(r"\*\*SHA-256:\*\*\s*`([0-9a-f]{64})`", teile[1].split("## ", 1)[0])
    assert treffer, f"{name} steht ohne Pruefsumme im Nachweis"
    roh = (Path(__file__).resolve().parent / "fixtures" / name).read_bytes()
    assert hashlib.sha256(roh).hexdigest() == treffer.group(1), (
        f"{name} weicht vom Nachweis ab — von Hand nachgebessert? Neu aufzeichnen."
    )
