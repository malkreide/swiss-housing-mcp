# Use Cases & Examples — swiss-housing-mcp

Real-world queries by audience. Every tool queries the public GWR/RegBL sources
and geo.admin.ch — **no API key is ever required.** Buildings are keyed by EGID,
dwellings by EWID.

## 🏫 Bildung & Schule

Lehrpersonen, Schulbehörden, Fachreferent:innen

### Baujahr und Kennzahlen eines Schulhauses

«Was weiss das Gebäuderegister über das Schulhaus an dieser Adresse — EGID, Baujahr, Gebäudekategorie?»

**API-Key nötig:** Nein

→ `address_to_egid("Seilergraben 76 Zürich")`
→ `lookup_building(<egid>)`

Warum nützlich: Schulbehörden können Alter, Kategorie und Fläche eines Schulgebäudes mit dem offiziellen Register belegen, statt auf Schätzungen zu vertrauen.

### Wohnungsbestand im Einzugsgebiet verstehen

«Wie viele Wohnungen gibt es in diesem Gebäude, und welche Zimmerzahlen dominieren?»

**API-Key nötig:** Nein

→ `lookup_dwellings(<egid>, canton="zh")`

Warum nützlich: Für die Schulraumplanung ist der Wohnungsbestand ein Frühindikator für die Zahl schulpflichtiger Kinder in einem Quartier.

## 👨‍👩‍👧 Eltern & Schulgemeinde

Elternräte, interessierte Erziehungsberechtigte

### Neubauten im Quartier verfolgen

«Welche Neubauten sind in unserer Gemeinde in den letzten Jahren dazugekommen?»

**API-Key nötig:** Nein

→ `new_construction(bfs_nr=<gemeinde>, ...)`
→ `construction_pipeline(bfs_nr=<gemeinde>)`

Warum nützlich: Eltern und Quartiervereine können Verdichtung und Zuzug faktenbasiert einordnen — relevant für Schulwege, Betreuungsplätze und Vereinsangebote.

### Ein Adress-Rätsel auflösen

«Zu welcher EGID gehört diese Adresse, und stimmen Gemeinde und Kanton?»

**API-Key nötig:** Nein

→ `address_to_egid("<Strasse Nr Ort>")`

Warum nützlich: Die EGID ist der Schlüssel, um eine Adresse eindeutig mit Register- und Statistikdaten zu verknüpfen.

## 🗳️ Bevölkerung & öffentliches Interesse

Allgemeine Öffentlichkeit, politisch und gesellschaftlich Interessierte

### Wohnbautätigkeit einer Gemeinde beurteilen

«Wie entwickelt sich der Wohnungsbau in dieser Gemeinde — Bestand, Neubau, Pipeline?»

**API-Key nötig:** Nein

→ `municipality_housing_stats(bfs_nr=<gemeinde>)`
→ `construction_pipeline(bfs_nr=<gemeinde>)`

Warum nützlich: Die Bevölkerung erhält einen faktenbasierten Blick auf Wohnungsknappheit und Bautätigkeit, statt sich auf einzelne Schlagzeilen zu verlassen.

### Register-Codes entschlüsseln

«Was bedeutet dieser GWR-Code in einem Gebäude- oder Wohnungsdatensatz?»

**API-Key nötig:** Nein

→ `explain_code(attribute="<feld>", code=<wert>, canton="zh")`

Warum nützlich: GWR-Merkmale sind kodiert; die Klartext-Auflösung macht Registerdaten für Laien lesbar.

## 🤖 KI-Interessierte & Entwickler:innen

MCP-Enthusiast:innen, Forscher:innen, Prompt Engineers, öffentliche Verwaltung

### Aktualität der Datenbasis prüfen

«Wie aktuell sind die kantonalen GWR-Dumps, die dieser Server verwendet?»

**API-Key nötig:** Nein

→ `dump_status()`

Warum nützlich: Vor einer Analyse können Agenten die Datenaktualität prüfen und Ergebnisse mit einem Stand-Datum versehen.

### Portfolio-Kombination: Raum, Register und Statistik

«Was gilt an dieser Adresse — Bauzone, Gebäude (EGID) und Gemeindestatistik?»

**API-Key nötig:** Nein

→ `address_to_egid("<Adresse>")` + `lookup_building(<egid>)` (housing)
→ `geo_zoning_at(x, y)` + `geo_municipality_at(x, y)` via https://github.com/malkreide/swiss-geodata-mcp
→ BFS-Nummer → Statistik via https://github.com/malkreide/swiss-statistics-mcp

Warum nützlich: Register-, Raum- und Statistik-Schicht sind bewusst getrennte Server; ein Agent kombiniert sie über die gemeinsame EGID-/LV95-/BFS-Brücke.

## 🔧 Technische Referenz: Tool-Auswahl nach Anwendungsfall

| Ich möchte… | Tool(s) | Auth nötig? |
|---|---|---|
| Ein Gebäude per EGID nachschlagen | `lookup_building` | Nein |
| Eine Adresse in eine EGID auflösen (Geocoding) | `address_to_egid` | Nein |
| Die Wohnungen eines Gebäudes auflisten | `lookup_dwellings` | Nein |
| Neubauten einer Gemeinde abrufen | `new_construction` | Nein |
| Die Bau-Pipeline einer Gemeinde ansehen | `construction_pipeline` | Nein |
| Gebäude in einer Bounding-Box finden | `buildings_in_bbox` | Nein |
| Wohnungs-Kennzahlen einer Gemeinde abrufen | `municipality_housing_stats` | Nein |
| Einen GWR-Code in Klartext auflösen | `explain_code` | Nein |
| Die Aktualität der Datenbasis prüfen | `dump_status` | Nein |
