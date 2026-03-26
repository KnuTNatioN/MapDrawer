# 2DM Format Specification (Version 1)

## Overview

`2DM` is a binary file format for 2D tile maps.
It is designed for simple game/editor workflows with:

- map width and height
- a tile-definition table
- optional door metadata with door IDs
- raw map data with **1 byte per cell**

The reference file extension is `.2dm`.
All integer values use **little-endian** byte order.

---

## Design goals

Version 1 is intentionally simple:

- easy to read and write in C, C++, Python, C#, Java, Rust, etc.
- easy to debug
- flexible enough for a small tile-definition header
- door IDs stored separately from map cells

Map cells are not bit-packed in V1.
Each cell uses **one full byte**.
This makes the format straightforward and extensible.

---

## Semantics used by the editor

The reference editor ships with these default tile IDs:

- `0` = Boden (walkable)
- `1` = Wand (blocked)
- `2` = Tür (walkable, has extra metadata)
- `3` = Spawn (walkable)

These meanings are stored in the tile-definition section of the file.
A reader can use those definitions instead of hardcoding names/colors.

---

## Binary layout

### File header

| Offset | Size | Type   | Name              | Description |
|-------:|-----:|--------|-------------------|-------------|
| 0      | 4    | bytes  | magic             | ASCII `2dM1` |
| 4      | 2    | uint16 | version           | format version, currently `1` |
| 6      | 2    | uint16 | tile_def_count    | number of tile-definition entries |
| 8      | 4    | uint32 | width             | map width in cells |
| 12     | 4    | uint32 | height            | map height in cells |
| 16     | 4    | uint32 | door_count        | number of door entries |

Total fixed header size: **20 bytes**.

---

## Tile definition entries

Immediately after the fixed header come `tile_def_count` tile-definition records.
Each record is variable-length.

### Tile definition layout

| Field       | Size | Type   | Description |
| Field       | Size | Type   | Description |
|-------------|-----:|--------|-------------|
| tile_id     | 1    | uint8  | numeric tile value used in the map data |
| flags       | 1    | uint8  | bit flags, see below |
| red         | 1    | uint8  | color red component |
| green       | 1    | uint8  | color green component |
| blue        | 1    | uint8  | color blue component |
| name_len    | 1    | uint8  | UTF-8 name length in bytes |
| name        | N    | bytes  | UTF-8 tile name |

### Flags

| Bit | Meaning |
|----:|---------|
| 0   | walkable |
| 1   | needs extra metadata |
| 2-7 | reserved, must be `0` in V1 |

### Example

A tile definition for `Tür` could look like:

- `tile_id = 2`
- `flags = 0b00000011` (`walkable` + `needs extra metadata`)
- color = `255, 59, 48`
- name = `Tür`

---

## Door entry list

Immediately after the tile-definition list come `door_count` door records.

### Door entry layout

| Field   | Size | Type   | Description |
|---------|-----:|--------|-------------|
| x       | 4    | uint32 | x coordinate in the map |
| y       | 4    | uint32 | y coordinate in the map |
| door_id | 4    | uint32 | user-defined door ID |

A door entry is valid only if the cell at `(x, y)` contains the tile value used for doors, usually `2`.

The editor does **not** enforce cross-map linking.
It only stores the door ID the user entered.
A game or toolchain can later resolve matching doors across maps.

---

## Map data block

After the door-entry list, the map data follows directly.

### Layout

- `width * height` bytes
- row-major order
- one byte per cell

### Row-major order

Cells are written left-to-right, top-to-bottom.

For a map with width `W` and height `H`, the byte index for cell `(x, y)` is:

`index = y * W + x`

### Example

For a `4 x 3` map:

```text
row 0: (0,0) (1,0) (2,0) (3,0)
row 1: (0,1) (1,1) (2,1) (3,1)
row 2: (0,2) (1,2) (2,2) (3,2)
```

The file stores 12 bytes in exactly that order.

---

## Validation rules

A valid V1 file should satisfy these conditions:

- magic must be `2dM1`
- version must be `1`
- width and height must both be `>= 1`
- exactly `tile_def_count` tile definitions must be present
- exactly `door_count` door entries must be present
- exactly `width * height` map bytes must be present
- no trailing bytes are expected in the reference implementation
- each door entry should point to a map cell that is a door tile

---

## Reference semantic model

A loader may expose the format like this:

```text
width: uint32
height: uint32
tile_defs: list of tile definitions
doors: list of door entries
grid: 2D array of uint8
```

Suggested in-memory structure:

```python
{
    "width": 100,
    "height": 80,
    "tile_defs": {
        0: {"name": "Boden", "color": "#ffffff", "walkable": True,  "needs_extra": False},
        1: {"name": "Wand",   "color": "#000000", "walkable": False, "needs_extra": False},
        2: {"name": "Tür",    "color": "#ff3b30", "walkable": True,  "needs_extra": True},
        3: {"name": "Spawn",  "color": "#34c759", "walkable": True,  "needs_extra": False},
    },
    "doors": {
        (12, 8): 1001,
        (40, 17): 1002,
    },
    "grid": [[...], [...], ...]
}
```

---

## Notes on future versions

Potential V2 extensions could include:

- additional object lists
- spawn groups
- map name or UUID
- target-map references for doors
- compression
- custom tile properties
- event triggers

Because V1 uses a version field and a structured header, later versions can evolve without breaking the format identifier style.

---

## Minimal writer algorithm

1. write fixed header
2. write tile-definition list
3. write door-entry list
4. write map data in row-major order

---

## Minimal reader algorithm

1. read and validate fixed header
2. read `tile_def_count` tile definitions
3. read `door_count` door entries
4. read exactly `width * height` map bytes
5. reshape the raw map bytes into a `height x width` grid

---

## Reference implementation files

- `two_d_map_editor.py` — Tkinter editor with palette, fill tool, line drawing, door IDs, zoom, open/save
- this document — binary format specification for `.2dm`
