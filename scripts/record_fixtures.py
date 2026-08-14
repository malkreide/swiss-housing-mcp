#!/usr/bin/env python3
"""Zeichnet echte Antworten der beiden Quellen nach `tests/fixtures/` auf.

Warum: eine handgeschriebene Fixture kodiert die Annahme ihres Autors und kann
sie deshalb nicht widerlegen. In `i14y-mcp` blieb genau deshalb eine ganze Suite
gruen, waehrend drei Tools produktiv leere Titel lieferten — die Stubs hatten
einen Schluessel erfunden und stimmten dem Mapper zu statt der Quelle.

Der GWR-Endpunkt liefert kein JSON, sondern ein ZIP mit einer SQLite-Datenbank,
die der Server per SQL abfragt. Aufgezeichnet wird deshalb ein ZIP mit
**wortgleichem Schema** und wenigen, zusammenhaengenden Zeilen: ein Gebaeude
mit seinen Eingaengen und Wohnungen. Die 47 Spalten von `building` bleiben
vollstaendig — genau sie sind die Satzform, die eine erfundene Fixture raten
muesste.

Herkunft, Datum, Auswahlregel und SHA-256 je Datei schreibt dieses Skript nach
`tests/fixtures/PROVENANCE.md`. Neu aufzeichnen:

    python scripts/record_fixtures.py

Braucht Netzzugang zu `public.madd.bfs.admin.ch` und `api3.geo.admin.ch`.
Entwicklungswerkzeug; weder das Paket noch die Testsuite importieren es.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

MADD = "https://public.madd.bfs.admin.ch"
GEOADMIN = "https://api3.geo.admin.ch/rest/services/api"
FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

# Appenzell Innerrhoden, der kleinste Kanton: 3.4 MB gepackt statt dreistelliger
# Megabyte. Fest gewaehlt, nicht «irgendeiner» — eine vom Lauf abhaengige Auswahl
# erzeugte bei jedem Aufzeichnen einen anderen Diff.
CANTON = "ai"

# Eine Adresse mit Absicht: fest, damit die Aufzeichnung reproduzierbar bleibt.
SEARCH_TEXT = "Bahnhofstrasse 1 Zuerich"


def fetch(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "swiss-housing-mcp-recorder"})
    with urlopen(req, timeout=300) as resp:
        return resp.read()


def trim_sqlite(quelle: Path, ziel: Path) -> dict[str, int]:
    """Kopiert Schema wortgleich und wenige, zusammenhaengende Zeilen."""
    src = sqlite3.connect(f"file:{quelle}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    dst = sqlite3.connect(ziel)

    # Schema unveraendert uebernehmen: die CREATE-Anweisungen der Quelle, nicht
    # nachgebaute. Ein nachgebautes Schema waere wieder eine Annahme.
    for (sql,) in src.execute("select sql from sqlite_master where sql is not null"):
        dst.execute(sql)

    # Ein Gebaeude, das auch Eingaenge und Wohnungen hat — sonst belegt die
    # Fixture die Verknuepfung nicht, auf der die Abfragen des Servers beruhen.
    egid = src.execute(
        "select b.EGID from building b "
        "where exists (select 1 from entrance e where e.EGID = b.EGID) "
        "and exists (select 1 from dwelling d where d.EGID = b.EGID) "
        "order by b.EGID limit 1"
    ).fetchone()[0]

    zahlen: dict[str, int] = {}
    for tabelle, where, params in (
        ("building", "where EGID = ?", (egid,)),
        ("entrance", "where EGID = ?", (egid,)),
        ("dwelling", "where EGID = ?", (egid,)),
        # `code` ist die Nachschlagetabelle, mit der der Server Zahlen in Text
        # uebersetzt — vollstaendig, sonst laufen Uebersetzungen ins Leere.
        ("code", "", ()),
        ("_metadata", "", ()),
    ):
        rows = [dict(r) for r in src.execute(f'select * from "{tabelle}" {where}', params)]
        if rows:
            spalten = ", ".join(f'"{k}"' for k in rows[0])
            platz = ", ".join("?" for _ in rows[0])
            dst.executemany(
                f'insert into "{tabelle}" ({spalten}) values ({platz})',
                [tuple(r.values()) for r in rows],
            )
        zahlen[tabelle] = len(rows)

    dst.commit()
    dst.close()
    src.close()
    zahlen["EGID"] = egid
    return zahlen


def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    recorded_at = datetime.now(UTC).strftime("%Y-%m-%d")
    entries: list[dict[str, Any]] = []
    print(f"Zeichne auf von {MADD} und {GEOADMIN}")

    def write_bytes(name: str, blob: bytes, url: str, rule: str) -> None:
        (FIXTURES / name).write_bytes(blob)
        entries.append(
            {
                "name": name,
                "url": url,
                "rule": rule,
                "bytes": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(),
            }
        )
        print(f"  ok  {name:<28} {len(blob):>8} B")

    def write_json(name: str, payload: Any, url: str, rule: str) -> None:
        write_bytes(
            name,
            (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
            url,
            rule,
        )

    # --- GWR-Dump: ZIP mit SQLite ---------------------------------------
    dump_url = f"{MADD}/{CANTON}.zip"
    print(f"  lade {dump_url} (einige MB) ...")
    roh = fetch(dump_url)
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        (tmpdir / "voll.zip").write_bytes(roh)
        with zipfile.ZipFile(tmpdir / "voll.zip") as zf:
            with zf.open("data.sqlite") as src, open(tmpdir / "voll.sqlite", "wb") as dst:
                shutil.copyfileobj(src, dst)
        zahlen = trim_sqlite(tmpdir / "voll.sqlite", tmpdir / "klein.sqlite")
        ziel = tmpdir / "dump.zip"
        with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(tmpdir / "klein.sqlite", "data.sqlite")
        write_bytes(
            f"gwr_{CANTON}.zip",
            ziel.read_bytes(),
            dump_url,
            f"ZIP mit `data.sqlite`; Schema wortgleich uebernommen. Gebaeude EGID "
            f"{zahlen['EGID']} mit {zahlen['entrance']} Eingaengen und "
            f"{zahlen['dwelling']} Wohnungen, `code` vollstaendig "
            f"({zahlen['code']} Zeilen), `_metadata` vollstaendig. Quelle: "
            f"{len(roh)} B gepackt",
        )

    # --- geo.admin: Adresssuche -----------------------------------------
    params = {"searchText": SEARCH_TEXT, "type": "locations", "limit": 3}
    url = f"{GEOADMIN}/SearchServer?{urlencode(params)}"
    write_json(
        "geoadmin_search.json",
        json.loads(fetch(url)),
        url,
        f"vollstaendig; Suche nach {SEARCH_TEXT!r}, hoechstens 3 Treffer",
    )

    # --- geo.admin: EGID-Nachschlag -------------------------------------
    egid = zahlen["EGID"]
    params = {
        "layer": "ch.bfs.gebaeude_wohnungs_register",
        "searchText": str(egid),
        "searchField": "egid",
        "returnGeometry": "false",
    }
    url = f"{GEOADMIN}/MapServer/find?{urlencode(params)}"
    write_json(
        "geoadmin_find_egid.json",
        json.loads(fetch(url)),
        url,
        f"vollstaendig; EGID {egid} — dasselbe Gebaeude wie im Dump oben",
    )

    _write_provenance(recorded_at, entries)
    print(f"\nPROVENANCE.md geschrieben, Aufzeichnungsdatum {recorded_at}")
    return 0


def _write_provenance(recorded_at: str, entries: list[dict[str, Any]]) -> None:
    lines = [
        "# Herkunft der Fixtures",
        "",
        "**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**",
        "",
        f"Aufgezeichnet am **{recorded_at}** von den beiden Quellen dieses Servers:",
        f"`{MADD}` und `{GEOADMIN}`.",
        "",
        "Ohne Datum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht",
        "mehr zu unterscheiden — die Datei sieht gleich aus.",
        "",
        "**Der GWR-Dump ist gekuerzt, aber nicht nachgebaut.** Die Quelle liefert",
        "kein JSON, sondern ein ZIP mit einer SQLite-Datenbank, die der Server per",
        "SQL abfragt. Die Aufzeichnung uebernimmt die `CREATE`-Anweisungen der",
        "Quelle **wortgleich** — ein nachgebautes Schema waere wieder eine",
        "Annahme — und fuellt sie mit wenigen, zusammenhaengenden Zeilen: ein",
        "Gebaeude mit seinen Eingaengen und Wohnungen. Die 47 Spalten von",
        "`building` bleiben vollstaendig. `code` und `_metadata` sind ganz dabei,",
        "weil der Server ueber `code` Zahlen in Text uebersetzt.",
        "",
        f"Kanton {CANTON.upper()} mit Absicht: der kleinste Dump. Eine vom Lauf",
        "abhaengige Auswahl erzeugte bei jedem Aufzeichnen einen anderen Diff.",
        "",
        "**Die beiden geo.admin-Aufzeichnungen zeigen dasselbe Gebaeude** wie der",
        "Dump. Damit belegt die Fixture nicht nur beide Antwortformen, sondern",
        "auch, dass die EGID ueber die Quellen hinweg dieselbe ist.",
        "",
        "Fehlerpfade — 404, Timeouts, leere Trefferlisten — bleiben",
        "handgeschrieben. Die lassen sich nicht auf Zuruf aufzeichnen.",
        "",
    ]
    for e in entries:
        lines += [
            f"## `{e['name']}`",
            "",
            f"- **Quelle:** `{e['url']}`",
            f"- **Aufgezeichnet:** {recorded_at}",
            f"- **Auswahl:** {e['rule']}",
            f"- **Groesse:** {e['bytes']} B",
            f"- **SHA-256:** `{e['sha256']}`",
            "",
        ]
    (FIXTURES / "PROVENANCE.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
