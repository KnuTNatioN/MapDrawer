# MapDrawer – 2D Karten-Editor

Ein schlanker, dateibasierter Karten-Editor für 2D-Spiele.
Karten werden im binären **`.2dm`**-Format gespeichert und können direkt von Godot, Unity oder jedem eigenen Game-Loop eingelesen werden.

---

## Features

| Werkzeug | Aktivierung | Beschreibung |
|---|---|---|
| Stift | Standardwerkzeug | Einzelne Zellen malen, per Drag überstreichen |
| Linie | Shift / Strg gedrückt halten | Bresenham-Linie vom Start- zum Endpunkt |
| Füllen | Toolbar-Button oder `F` | Flood-Fill (BFS) eines zusammenhängenden Bereichs |
| Kreis | Toolbar-Button oder `C` | Mittelpunkt-Algorithmus; Drag bestimmt Radius |
| Radierer | Rechtsklick | Setzt Zelle auf Boden (Tile 0) zurück |

**Weitere Funktionen**

- Undo / Redo (50 Schritte) – `Strg+Z` / `Strg+Y`
- Zoom per Mausrad oder Schieberegler (6 – 64 px/Zelle)
- Gitter ein-/ausblenden – `G`
- Neue Map / Öffnen / Speichern / Speichern unter
- Tür-IDs per Doppelklick auf eine Tür-Zelle bearbeiten

---

## Standard-Kacheln

| ID | Name | Farbe | Begehbar | Extras |
|---|---|---|---|---|
| 0 | Boden | Weiß | Ja | – |
| 1 | Wand | Schwarz | Nein | – |
| 2 | Tür | Rot | Ja | Tür-ID (uint32) |
| 3 | Spawn | Grün | Ja | – |

---

## Download (fertige Programme)

Vorkompilierte Einzeldateien findest du unter **Releases** (rechte Seite dieser Seite):

| Datei | Betriebssystem |
|---|---|
| `MapDrawer.exe` | Windows 10/11 (64-Bit), keine Installation nötig |
| `MapDrawer` | Linux (Ubuntu 22.04+, 64-Bit), `chmod +x` erforderlich |

---

## Aus dem Quellcode starten

Benötigt: **Python 3.10+** (mit Tkinter, ist in der Standard-Installation enthalten)

```bash
# Icons (optional, aber empfohlen)
pip install Pillow

# Editor starten
python main.py
```

Ohne Pillow starten die Icons als Text-Fallback – alle Funktionen bleiben erhalten.

---

## Das `.2dm` Dateiformat

`.2dm` ist ein kompaktes Binärformat (little-endian) für 2D-Kachelkarten.
Magic-Bytes: `2dM1` | Aktuelle Version: `1`

### Dateiaufbau (der Reihe nach)

```
[Header – 20 Byte fix]
[Kachel-Definitionen – variabel]
[Tür-Einträge – je 12 Byte]
[Map-Daten – width × height Byte]
```

### Header (20 Byte)

| Offset | Größe | Typ | Feld | Beschreibung |
|---:|---:|---|---|---|
| 0 | 4 | bytes | magic | ASCII `2dM1` |
| 4 | 2 | uint16 | version | Formatversion (aktuell `1`) |
| 6 | 2 | uint16 | tile\_def\_count | Anzahl Kachel-Definitionen |
| 8 | 4 | uint32 | width | Kartenbreite in Zellen |
| 12 | 4 | uint32 | height | Kartenhöhe in Zellen |
| 16 | 4 | uint32 | door\_count | Anzahl Tür-Einträge |

### Kachel-Definition (variabel)

| Größe | Typ | Feld | Beschreibung |
|---:|---|---|---|
| 1 | uint8 | tile\_id | Numerischer Kachelwert in den Map-Daten |
| 1 | uint8 | flags | Bit 0 = begehbar, Bit 1 = braucht Extras |
| 1 | uint8 | red | Farbe Rot |
| 1 | uint8 | green | Farbe Grün |
| 1 | uint8 | blue | Farbe Blau |
| 1 | uint8 | name\_len | Länge des UTF-8-Namens in Byte |
| N | bytes | name | UTF-8-Name der Kachel |

### Tür-Eintrag (12 Byte)

| Größe | Typ | Feld | Beschreibung |
|---:|---|---|---|
| 4 | uint32 | x | X-Koordinate in der Karte |
| 4 | uint32 | y | Y-Koordinate in der Karte |
| 4 | uint32 | door\_id | Frei wählbare Tür-ID (z. B. für Raumverknüpfung) |

### Map-Daten

`width × height` Bytes in **Row-major-Reihenfolge** (links→rechts, oben→unten).
Byte-Index einer Zelle `(x, y)`: `index = y × width + x`

Jedes Byte enthält die `tile_id` der entsprechenden Kachel.

### Minimalleser (Python)

```python
import struct

HEADER = struct.Struct("<4sHHIII")
DOOR   = struct.Struct("<III")

with open("map.2dm", "rb") as f:
    magic, version, tile_count, width, height, door_count = HEADER.unpack(f.read(20))
    assert magic == b"2dM1" and version == 1

    tile_defs = {}
    for _ in range(tile_count):
        tile_id, flags, r, g, b, name_len = struct.unpack("<BBBBBB", f.read(6))
        name = f.read(name_len).decode()
        tile_defs[tile_id] = {"name": name, "walkable": bool(flags & 1)}

    doors = {}
    for _ in range(door_count):
        x, y, door_id = DOOR.unpack(f.read(12))
        doors[(x, y)] = door_id

    raw = f.read(width * height)
    grid = [[raw[y * width + x] for x in range(width)] for y in range(height)]
```

### Validierungsregeln

- Magic muss `2dM1` sein
- Version muss `1` sein
- `width` und `height` müssen ≥ 1 sein
- Exakt `tile_def_count` Kachel-Definitionen müssen folgen
- Exakt `door_count` Tür-Einträge müssen folgen
- Exakt `width × height` Map-Bytes müssen folgen (keine übrigen Bytes)
- Jede Tür-Koordinate muss auf eine Tür-Kachel zeigen

---

## Projektstruktur

```
MapDrawer/
├── main.py            # Einstiegspunkt
├── core/
│   ├── codec.py       # .2dm Lesen / Schreiben
│   ├── config.py      # Konstanten, Standard-Kacheln
│   └── model.py       # Datenmodell, Undo/Redo, Algorithmen
├── ui/
│   ├── controller.py  # Verbindet Model und View, Event-Handler
│   ├── view.py        # Tkinter-Fenster, Canvas, Werkzeugleiste
│   └── dialogs.py     # Start-, Neu-Map-, Tür-ID-Dialoge
└── fonts/
    └── fa-solid-900.ttf   # Font Awesome (optional, für Icons)
```

---

## Lizenz

siehe [LICENSE](LICENSE)
