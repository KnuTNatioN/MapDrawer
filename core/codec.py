import struct
from typing import Dict, Tuple

from .config import MAGIC, VERSION


class TwoDMapCodec:
    """Binary format codec for .2dm files.

    File structure (little-endian):
      4 bytes  magic  '2dM1'
      2 bytes  version          (uint16)
      2 bytes  tile-def count   (uint16)
      4 bytes  width            (uint32)
      4 bytes  height           (uint32)
      4 bytes  door-entry count (uint32)

      Tile definitions – repeated tile_count times:
        1 byte   tile_id
        1 byte   flags  (bit0 = walkable, bit1 = needs_extra)
        1 byte   R, 1 byte G, 1 byte B
        1 byte   UTF-8 name length N
        N bytes  UTF-8 tile name

      Door entries – repeated door_count times:
        4 bytes x  (uint32)
        4 bytes y  (uint32)
        4 bytes door_id (uint32)

      Map data: width * height bytes, row-major, 1 byte per cell
    """

    HEADER_STRUCT = struct.Struct("<4sHHIII")
    DOOR_STRUCT   = struct.Struct("<III")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hex_to_rgb(color: str) -> Tuple[int, int, int]:
        color = color.lstrip("#")
        if len(color) != 6:
            raise ValueError(f"Ungültige Farbe: {color!r}")
        return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)

    @staticmethod
    def _rgb_to_hex(r: int, g: int, b: int) -> str:
        return f"#{r:02x}{g:02x}{b:02x}"

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    @classmethod
    def save(
        cls,
        path: str,
        width: int,
        height: int,
        grid: list,
        tile_defs: Dict[int, dict],
        doors: Dict[Tuple[int, int], int],
    ) -> None:
        flat = [cell for row in grid for cell in row]
        tile_ids_present = sorted(tile_defs.keys())
        door_items = sorted(
            (x, y, door_id) for (x, y), door_id in doors.items()
        )

        with open(path, "wb") as f:
            f.write(
                cls.HEADER_STRUCT.pack(
                    MAGIC, VERSION, len(tile_ids_present),
                    width, height, len(door_items),
                )
            )

            for tile_id in tile_ids_present:
                entry = tile_defs[tile_id]
                flags = 0
                if entry.get("walkable"):
                    flags |= 0b00000001
                if entry.get("needs_extra"):
                    flags |= 0b00000010
                r, g, b = cls._hex_to_rgb(entry["color"])
                name_bytes = entry["name"].encode("utf-8")
                if len(name_bytes) > 255:
                    raise ValueError(f"Tile-Name zu lang: {entry['name']!r}")
                f.write(
                    struct.pack("<BBBBBB", tile_id, flags, r, g, b, len(name_bytes))
                )
                f.write(name_bytes)

            for x, y, door_id in door_items:
                f.write(cls.DOOR_STRUCT.pack(x, y, door_id))

            f.write(bytes(flat))

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: str) -> dict:
        with open(path, "rb") as f:
            header_bytes = f.read(cls.HEADER_STRUCT.size)
            if len(header_bytes) != cls.HEADER_STRUCT.size:
                raise ValueError("Datei ist zu klein für einen gültigen Header.")

            magic, version, tile_count, width, height, door_count = (
                cls.HEADER_STRUCT.unpack(header_bytes)
            )

            if magic != MAGIC:
                raise ValueError("Ungültige Dateikennung. Erwartet wird '2dM1'.")
            if version != VERSION:
                raise ValueError(f"Nicht unterstützte Version: {version}")
            if width < 1 or height < 1:
                raise ValueError("Ungültige Map-Größe im Header.")

            tile_defs: Dict[int, dict] = {}
            for _ in range(tile_count):
                fixed = f.read(6)
                if len(fixed) != 6:
                    raise ValueError("Tile-Definition unvollständig.")
                tile_id, flags, r, g, b, name_len = struct.unpack("<BBBBBB", fixed)
                name_bytes = f.read(name_len)
                if len(name_bytes) != name_len:
                    raise ValueError("Tile-Name unvollständig.")
                tile_defs[tile_id] = {
                    "name":        name_bytes.decode("utf-8"),
                    "color":       cls._rgb_to_hex(r, g, b),
                    "walkable":    bool(flags & 0b00000001),
                    "needs_extra": bool(flags & 0b00000010),
                }

            doors: Dict[Tuple[int, int], int] = {}
            for _ in range(door_count):
                door_bytes = f.read(cls.DOOR_STRUCT.size)
                if len(door_bytes) != cls.DOOR_STRUCT.size:
                    raise ValueError("Türliste unvollständig.")
                x, y, door_id = cls.DOOR_STRUCT.unpack(door_bytes)
                doors[(x, y)] = door_id

            cell_count = width * height
            raw_map = f.read(cell_count)
            if len(raw_map) != cell_count:
                raise ValueError(
                    f"Map-Daten unvollständig. "
                    f"Erwartet {cell_count} Bytes, erhalten {len(raw_map)}."
                )
            if f.read(1):
                raise ValueError(
                    "Datei enthält zusätzliche unerwartete Bytes am Ende."
                )

        grid = []
        idx = 0
        for _y in range(height):
            row = []
            for _x in range(width):
                row.append(raw_map[idx])
                idx += 1
            grid.append(row)

        return {
            "width":     width,
            "height":    height,
            "grid":      grid,
            "tile_defs": tile_defs,
            "doors":     doors,
        }
