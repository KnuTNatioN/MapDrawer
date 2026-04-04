import struct
import pytest
from pathlib import Path
from core.codec import TwoDMapCodec
from core.config import MAGIC, VERSION, TILE_DEFS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SIMPLE_TILE_DEFS = {
    0: {"name": "Boden", "color": "#ffffff", "walkable": True,  "needs_extra": False},
    1: {"name": "Wand",  "color": "#000000", "walkable": False, "needs_extra": False},
}


def make_grid(width, height, fill=0):
    return [[fill] * width for _ in range(height)]


def round_trip(tmp_path, width, height, grid, tile_defs, doors):
    path = str(tmp_path / "map.2dm")
    TwoDMapCodec.save(path, width, height, grid, tile_defs, doors)
    return TwoDMapCodec.load(path)


# ---------------------------------------------------------------------------
# _hex_to_rgb
# ---------------------------------------------------------------------------

class TestHexToRgb:
    def test_white(self):
        assert TwoDMapCodec._hex_to_rgb("#ffffff") == (255, 255, 255)

    def test_black(self):
        assert TwoDMapCodec._hex_to_rgb("#000000") == (0, 0, 0)

    def test_specific_color(self):
        assert TwoDMapCodec._hex_to_rgb("#ff3b30") == (255, 59, 48)

    def test_without_hash_prefix(self):
        assert TwoDMapCodec._hex_to_rgb("34c759") == (52, 199, 89)

    def test_invalid_short_raises(self):
        with pytest.raises(ValueError):
            TwoDMapCodec._hex_to_rgb("#fff")

    def test_invalid_characters_raise(self):
        with pytest.raises(ValueError):
            TwoDMapCodec._hex_to_rgb("#zzzzzz")


# ---------------------------------------------------------------------------
# _rgb_to_hex
# ---------------------------------------------------------------------------

class TestRgbToHex:
    def test_white(self):
        assert TwoDMapCodec._rgb_to_hex(255, 255, 255) == "#ffffff"

    def test_black(self):
        assert TwoDMapCodec._rgb_to_hex(0, 0, 0) == "#000000"

    def test_specific_color(self):
        assert TwoDMapCodec._rgb_to_hex(255, 59, 48) == "#ff3b30"

    def test_zero_padding(self):
        assert TwoDMapCodec._rgb_to_hex(1, 2, 3) == "#010203"

    def test_roundtrip_hex_rgb_hex(self):
        for color in ["#ff3b30", "#34c759", "#007aff", "#000000", "#ffffff"]:
            r, g, b = TwoDMapCodec._hex_to_rgb(color)
            assert TwoDMapCodec._rgb_to_hex(r, g, b) == color


# ---------------------------------------------------------------------------
# save / load – round-trip tests
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_simple_map_dimensions(self, tmp_path):
        result = round_trip(tmp_path, 4, 3, make_grid(4, 3), SIMPLE_TILE_DEFS, {})
        assert result["width"] == 4
        assert result["height"] == 3

    def test_grid_data_preserved(self, tmp_path):
        grid = [[0, 1, 0], [1, 0, 1], [0, 1, 0]]
        result = round_trip(tmp_path, 3, 3, grid, SIMPLE_TILE_DEFS, {})
        assert result["grid"] == grid

    def test_tile_name_preserved(self, tmp_path):
        result = round_trip(tmp_path, 2, 2, make_grid(2, 2), SIMPLE_TILE_DEFS, {})
        assert result["tile_defs"][0]["name"] == "Boden"

    def test_tile_color_preserved(self, tmp_path):
        result = round_trip(tmp_path, 2, 2, make_grid(2, 2), SIMPLE_TILE_DEFS, {})
        assert result["tile_defs"][0]["color"] == "#ffffff"

    def test_walkable_flag_preserved(self, tmp_path):
        result = round_trip(tmp_path, 2, 2, make_grid(2, 2), SIMPLE_TILE_DEFS, {})
        assert result["tile_defs"][0]["walkable"] is True
        assert result["tile_defs"][1]["walkable"] is False

    def test_needs_extra_flag_preserved(self, tmp_path):
        tile_defs = {
            2: {"name": "Tür", "color": "#ff3b30", "walkable": True, "needs_extra": True},
        }
        grid = [[2, 2], [2, 2]]
        doors = {(0, 0): 0, (1, 0): 1, (0, 1): 2, (1, 1): 3}
        result = round_trip(tmp_path, 2, 2, grid, tile_defs, doors)
        assert result["tile_defs"][2]["needs_extra"] is True

    def test_doors_preserved(self, tmp_path):
        tile_defs = dict(SIMPLE_TILE_DEFS)
        tile_defs[2] = {"name": "Tür", "color": "#ff3b30", "walkable": True, "needs_extra": True}
        grid = make_grid(5, 5)
        grid[2][2] = 2
        doors = {(2, 2): 7}
        result = round_trip(tmp_path, 5, 5, grid, tile_defs, doors)
        assert result["doors"] == {(2, 2): 7}

    def test_no_doors_returns_empty_dict(self, tmp_path):
        result = round_trip(tmp_path, 3, 3, make_grid(3, 3), SIMPLE_TILE_DEFS, {})
        assert result["doors"] == {}

    def test_multiple_doors(self, tmp_path):
        tile_defs = dict(SIMPLE_TILE_DEFS)
        tile_defs[2] = {"name": "Tür", "color": "#ff3b30", "walkable": True, "needs_extra": True}
        grid = make_grid(5, 5)
        grid[0][0] = 2
        grid[0][4] = 2
        grid[4][2] = 2
        doors = {(0, 0): 1, (4, 0): 2, (2, 4): 3}
        result = round_trip(tmp_path, 5, 5, grid, tile_defs, doors)
        assert result["doors"] == doors

    def test_all_standard_tiles(self, tmp_path):
        grid = [[0, 1, 2, 3]]
        tile_defs = dict(TILE_DEFS)
        doors = {(2, 0): 0}
        result = round_trip(tmp_path, 4, 1, grid, tile_defs, doors)
        assert result["grid"] == grid

    def test_large_map(self, tmp_path):
        w, h = 100, 80
        result = round_trip(tmp_path, w, h, make_grid(w, h), SIMPLE_TILE_DEFS, {})
        assert result["width"] == w
        assert result["height"] == h
        assert len(result["grid"]) == h
        assert len(result["grid"][0]) == w

    def test_1x1_map(self, tmp_path):
        result = round_trip(tmp_path, 1, 1, [[1]], SIMPLE_TILE_DEFS, {})
        assert result["grid"] == [[1]]

    def test_unicode_tile_name(self, tmp_path):
        tile_defs = {
            0: {"name": "Böden", "color": "#ffffff", "walkable": True, "needs_extra": False},
        }
        result = round_trip(tmp_path, 2, 2, make_grid(2, 2), tile_defs, {})
        assert result["tile_defs"][0]["name"] == "Böden"

    def test_grid_row_order_preserved(self, tmp_path):
        # Each row has a distinct value to verify row ordering
        grid = [[0, 0], [1, 1], [0, 1]]
        result = round_trip(tmp_path, 2, 3, grid, SIMPLE_TILE_DEFS, {})
        assert result["grid"][0] == [0, 0]
        assert result["grid"][1] == [1, 1]
        assert result["grid"][2] == [0, 1]


# ---------------------------------------------------------------------------
# load – error cases
# ---------------------------------------------------------------------------

class TestLoadErrors:
    def _write(self, tmp_path, data: bytes) -> str:
        path = str(tmp_path / "bad.2dm")
        Path(path).write_bytes(data)
        return path

    def _valid_header(self, tile_count=0, width=2, height=2, door_count=0) -> bytes:
        return struct.pack("<4sHHIII", MAGIC, VERSION, tile_count, width, height, door_count)

    def test_file_too_small_for_header(self, tmp_path):
        path = self._write(tmp_path, b"\x00" * 4)
        with pytest.raises(ValueError, match="zu klein"):
            TwoDMapCodec.load(path)

    def test_wrong_magic_raises(self, tmp_path):
        header = struct.pack("<4sHHIII", b"XXXX", VERSION, 0, 2, 2, 0)
        path = self._write(tmp_path, header + bytes(4))
        with pytest.raises(ValueError, match="Dateikennung"):
            TwoDMapCodec.load(path)

    def test_wrong_version_raises(self, tmp_path):
        header = struct.pack("<4sHHIII", MAGIC, 99, 0, 2, 2, 0)
        path = self._write(tmp_path, header + bytes(4))
        with pytest.raises(ValueError, match="Version"):
            TwoDMapCodec.load(path)

    def test_zero_width_raises(self, tmp_path):
        header = struct.pack("<4sHHIII", MAGIC, VERSION, 0, 0, 2, 0)
        path = self._write(tmp_path, header)
        with pytest.raises(ValueError, match="Größe"):
            TwoDMapCodec.load(path)

    def test_zero_height_raises(self, tmp_path):
        header = struct.pack("<4sHHIII", MAGIC, VERSION, 0, 2, 0, 0)
        path = self._write(tmp_path, header)
        with pytest.raises(ValueError, match="Größe"):
            TwoDMapCodec.load(path)

    def test_truncated_map_data_raises(self, tmp_path):
        header = self._valid_header(width=4, height=4)
        # 4×4 = 16 bytes needed, only 8 provided
        path = self._write(tmp_path, header + bytes(8))
        with pytest.raises(ValueError, match="unvollständig"):
            TwoDMapCodec.load(path)

    def test_extra_bytes_at_end_raises(self, tmp_path):
        header = self._valid_header(width=2, height=2)
        path = self._write(tmp_path, header + bytes(4) + b"\xff")
        with pytest.raises(ValueError, match="zusätzliche"):
            TwoDMapCodec.load(path)

    def test_truncated_tile_def_raises(self, tmp_path):
        # Claim 1 tile def but only give 3 bytes
        header = self._valid_header(tile_count=1, width=2, height=2)
        path = self._write(tmp_path, header + b"\x00\x00\x00")
        with pytest.raises(ValueError, match="unvollständig"):
            TwoDMapCodec.load(path)

    def test_truncated_door_list_raises(self, tmp_path):
        # Claim 1 door entry but only give 4 bytes (needs 12)
        header = self._valid_header(width=2, height=2, door_count=1)
        path = self._write(tmp_path, header + bytes(4) + b"\x00\x00\x00\x00")
        with pytest.raises(ValueError, match="unvollständig"):
            TwoDMapCodec.load(path)
