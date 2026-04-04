# Plan: Map-Resize nach dem Öffnen

Branch: `feature/resizeMap`

## Ziel

Der Nutzer soll die Größe einer bereits geöffneten Map nachträglich ändern können — inklusive Ankerpunkt-Auswahl, Fill-Tile für neue Zellen und vollständigem Undo/Redo-Support.

---

## Zu ändernde Dateien (Übersicht)

| Datei | Aufwand | Was |
|---|---|---|
| `ui/dialogs.py` | mittel | Neue `ResizeMapDialog`-Klasse |
| `core/model.py` | mittel | `resize()`-Methode |
| `ui/controller.py` | klein | `resize_map()` + Undo-Logik erweitern |
| `ui/view.py` | klein | Button/Menüeintrag hinzufügen |
| `core/codec.py` | keine | Keine Änderungen nötig |

---

## 1. `ui/dialogs.py` — Neue `ResizeMapDialog`-Klasse

Ähnlich wie `NewMapDialog`, aber mit aktuellen Werten vorbelegt.

### Felder:
- **Neue Breite** (`IntVar`, vorbelegt mit `model.width`, Bereich 1–4096)
- **Neue Höhe** (`IntVar`, vorbelegt mit `model.height`, Bereich 1–4096)
- **Ankerpunkt** — 3×3 Raster aus Radio-Buttons (welcher Teil des Inhalts bleibt erhalten):
  ```
  [↖] [↑] [↗]
  [←] [·] [→]
  [↙] [↓] [↘]
  ```
  Wert als String: `"nw"`, `"n"`, `"ne"`, `"w"`, `"c"`, `"e"`, `"sw"`, `"s"`, `"se"`  
  Standard: `"nw"` (Inhalt bleibt oben-links, Erweiterung nach rechts/unten)
- **Fill-Tile** (`IntVar`, Standard: `0` = Boden) — welche Tile neue leere Zellen bekommen
- **Warnung** wenn neue Größe kleiner als aktuelle: Label mit rotem Text ("Daten außerhalb der neuen Grenzen gehen verloren")

### Rückgabe (`dlg.result`):
```python
{
    "width": int,
    "height": int,
    "anchor": str,   # z.B. "nw"
    "fill_tile": int
}
# oder None bei Abbruch
```

---

## 2. `core/model.py` — `MapModel.resize()`

### Signatur:
```python
def resize(self, new_width: int, new_height: int, anchor: str, fill_tile: int) -> None
```

### Ablauf:

#### Schritt 1: Offset berechnen
Der Ankerpunkt bestimmt, wie weit der bestehende Inhalt in das neue Grid verschoben wird.

```
anchor "nw" → offset_x = 0,                     offset_y = 0
anchor "n"  → offset_x = (new_w - old_w) // 2,  offset_y = 0
anchor "ne" → offset_x = new_w - old_w,          offset_y = 0
anchor "w"  → offset_x = 0,                     offset_y = (new_h - old_h) // 2
anchor "c"  → offset_x = (new_w - old_w) // 2,  offset_y = (new_h - old_h) // 2
anchor "e"  → offset_x = new_w - old_w,          offset_y = (new_h - old_h) // 2
anchor "sw" → offset_x = 0,                     offset_y = new_h - old_h
anchor "s"  → offset_x = (new_w - old_w) // 2,  offset_y = new_h - old_h
anchor "se" → offset_x = new_w - old_w,          offset_y = new_h - old_h
```

Negative Offsets bedeuten: der Inhalt wird oben/links beschnitten.

#### Schritt 2: Neues Grid anlegen
```python
new_grid = [[fill_tile] * new_width for _ in range(new_height)]
```

#### Schritt 3: Alten Inhalt hineinkopieren
Für jede Zelle `(x, y)` des alten Grids:
- Zielposition: `(x + offset_x, y + offset_y)`
- Nur kopieren wenn Zielposition innerhalb `[0, new_width)` × `[0, new_height)`

#### Schritt 4: Doors anpassen
Für jeden Door-Eintrag `(ox, oy) → door_id`:
- Neue Position: `(ox + offset_x, oy + offset_y)`
- Nur übernehmen wenn neue Position innerhalb der neuen Grenzen liegt
- Doors außerhalb werden stillschweigend entfernt

#### Schritt 5: Modell aktualisieren
```python
self.width = new_width
self.height = new_height
self.grid = new_grid
self.doors = new_doors
```
Undo-Stack **nicht** hier leeren — das übernimmt der Controller (siehe Abschnitt 3).

---

## 3. `ui/controller.py` — `resize_map()` + Undo-Erweiterung

### Neue Methode `resize_map()`:
```
1. ResizeMapDialog öffnen (aktuelle model.width / model.height übergeben)
2. Bei Abbruch: return
3. Snapshot vor dem Resize anlegen:
   snapshot = ("resize", model.width, model.height, deep_copy(model.grid), dict(model.doors))
4. model.undo_stack.append([snapshot])   ← als einelementige Liste (wie andere Aktionen)
5. model.redo_stack.clear()
6. model.resize(new_width, new_height, anchor, fill_tile) aufrufen
7. view.full_redraw() aufrufen
8. Titelleiste aktualisieren
```

### Undo/Redo-Logik erweitern (in `undo()` und `redo()`):

Der Stack enthält entweder:
- **Normal**: `[(x, y, old_tile, new_tile, old_door, new_door), ...]`
- **Resize**: `[("resize", old_w, old_h, old_grid, old_doors)]` ← einelementige Liste mit Tuple das mit `"resize"` beginnt

Erkennungs-Check am Anfang von `undo()` / `redo()`:
```python
action = stack.pop()
if action[0][0] == "resize":
    # Resize rückgängig machen:
    # Aktuellen Zustand als Redo-Snapshot sichern, dann alten Zustand wiederherstellen
    _, old_w, old_h, old_grid, old_doors = action[0]
    # ... Redo-Snapshot: aktuellen Zustand speichern
    model.width, model.height = old_w, old_h
    model.grid = old_grid
    model.doors = old_doors
    view.full_redraw()
else:
    # bestehende Logik für normale Zell-Änderungen
```

---

## 4. `ui/view.py` — Button/Menüeintrag

### Option A: Toolbar-Button
In der bestehenden Toolbar-Reihe (Neu, Öffnen, Speichern, Undo, Redo) einen "Resize"-Button ergänzen.  
Label: `⤢` oder Text `"Resize"`.  
Command: `controller.resize_map`

### Option B: Menüleiste (empfohlen falls vorhanden, sonst Option A)
Unter einem "Map"-Menü: `Map → Resize...`

Prüfen ob bereits eine Menüleiste existiert — falls nicht, bei Option A bleiben.

---

## 5. `core/codec.py` — Keine Änderungen

Breite und Höhe werden bereits direkt aus `model.width` / `model.height` ins Binary-Format geschrieben. Eine resizete Map wird korrekt gespeichert und geladen ohne weitere Anpassungen.

---

## Randnotizen / Stolperstellen

- **Offset kann negativ werden** (beim Verkleinern mit bestimmten Ankern) — das ist korrekt, einfach den Quellbereich entsprechend clippen.
- **Deep Copy für Grid-Snapshot** zwingend notwendig (`copy.deepcopy(model.grid)`), sonst referenziert der Snapshot dasselbe Objekt.
- **Doors im Snapshot** ebenfalls kopieren (`dict(model.doors)` reicht, da Werte primitive Ints sind).
- **Max Undo-Einträge** (`MAX_UNDO = 50`) gilt auch für Resize-Aktionen — kein Sonderfall nötig.
- **Warnung im Dialog** nur anzeigen wenn `new_width < old_width OR new_height < old_height`.
