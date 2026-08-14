# Herkunft der Fixtures

**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**

Aufgezeichnet am **2026-08-14** von den beiden Quellen dieses Servers:
`https://public.madd.bfs.admin.ch` und `https://api3.geo.admin.ch/rest/services/api`.

Ohne Datum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht
mehr zu unterscheiden — die Datei sieht gleich aus.

**Der GWR-Dump ist gekuerzt, aber nicht nachgebaut.** Die Quelle liefert
kein JSON, sondern ein ZIP mit einer SQLite-Datenbank, die der Server per
SQL abfragt. Die Aufzeichnung uebernimmt die `CREATE`-Anweisungen der
Quelle **wortgleich** — ein nachgebautes Schema waere wieder eine
Annahme — und fuellt sie mit wenigen, zusammenhaengenden Zeilen: ein
Gebaeude mit seinen Eingaengen und Wohnungen. Die 47 Spalten von
`building` bleiben vollstaendig. `code` und `_metadata` sind ganz dabei,
weil der Server ueber `code` Zahlen in Text uebersetzt.

Kanton AI mit Absicht: der kleinste Dump. Eine vom Lauf
abhaengige Auswahl erzeugte bei jedem Aufzeichnen einen anderen Diff.

**Die beiden geo.admin-Aufzeichnungen zeigen dasselbe Gebaeude** wie der
Dump. Damit belegt die Fixture nicht nur beide Antwortformen, sondern
auch, dass die EGID ueber die Quellen hinweg dieselbe ist.

Fehlerpfade — 404, Timeouts, leere Trefferlisten — bleiben
handgeschrieben. Die lassen sich nicht auf Zuruf aufzeichnen.

## `gwr_ai.zip`

- **Quelle:** `https://public.madd.bfs.admin.ch/ai.zip`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** ZIP mit `data.sqlite`; Schema wortgleich uebernommen. Gebaeude EGID 1712079 mit 1 Eingaengen und 1 Wohnungen, `code` vollstaendig (405 Zeilen), `_metadata` vollstaendig. Quelle: 3410829 B gepackt
- **Groesse:** 18124 B
- **SHA-256:** `b2c85213ab70d9e098d926b2f30763b8370912065965fe952bd477414847af5a`

## `geoadmin_search.json`

- **Quelle:** `https://api3.geo.admin.ch/rest/services/api/SearchServer?searchText=Bahnhofstrasse+1+Zuerich&type=locations&limit=3`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendig; Suche nach 'Bahnhofstrasse 1 Zuerich', hoechstens 3 Treffer
- **Groesse:** 3348 B
- **SHA-256:** `f52be4ba7f14abadab907fd7afa711f6e13410556be435cc518183d9a30f68fd`

## `geoadmin_find_egid.json`

- **Quelle:** `https://api3.geo.admin.ch/rest/services/api/MapServer/find?layer=ch.bfs.gebaeude_wohnungs_register&searchText=1712079&searchField=egid&returnGeometry=false`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendig; EGID 1712079 — dasselbe Gebaeude wie im Dump oben
- **Groesse:** 5031 B
- **SHA-256:** `cc113682d23f9a47aefc8b60ce61918a60590d3b27ce8dedd1a2d50039e8bc96`
