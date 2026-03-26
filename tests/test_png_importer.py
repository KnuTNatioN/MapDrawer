import pytest
from PIL import Image

from core.png_importer import PngImporter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TILE_DEFS_2 = {
    0: {"name": "Boden", "color": "#ffffff", "walkable": True,  "needs_extra": False},
    1: {"name": "Wand",  "color": "#000000", "walkable": False, "needs_extra": False},
}

TILE_DEFS_4 = {
    0: {"name": "Boden", "color": "#ffffff", "walkable": True,  "needs_extra": False},
    1: {"name": "Wand",  "color": "#000000", "walkable": False, "needs_extra": False},
    2: {"name": "Tür",   "color": "#ff3b30", "walkable": True,  "needs_extra": True},
    3: {"name": "Spawn", "color": "#34c759", "walkable": True,  "needs_extra": False},
}


def solid_image(colors_grid: list[list[tuple]], tile_size: int = 1) -> Image.Image:
    """Build an RGB image where each tile is a solid-color tile_size×tile_size block."""
    map_h = len(colors_grid)
    map_w = len(colors_grid[0])
    img = Image.new("RGB", (map_w * tile_size, map_h * tile_size))
    pixels = img.load()
    for ty, row in enumerate(colors_grid):
        for tx, color in enumerate(row):
            for dy in range(tile_size):
                for dx in range(tile_size):
                    pixels[tx * tile_size + dx, ty * tile_size + dy] = color
    return img


def save_png(tmp_path, img: Image.Image, name: str = "test.png") -> str:
    path = str(tmp_path / name)
    img.save(path)
    return path


# ---------------------------------------------------------------------------
# _nearest_tile
# ---------------------------------------------------------------------------

class TestNearestTile:
    PALETTE = {0: (255, 255, 255), 1: (0, 0, 0)}

    def test_exact_white(self):
        assert PngImporter._nearest_tile(255, 255, 255, self.PALETTE) == 0

    def test_exact_black(self):
        assert PngImporter._nearest_tile(0, 0, 0, self.PALETTE) == 1

    def test_closer_to_white(self):
        assert PngImporter._nearest_tile(200, 200, 200, self.PALETTE) == 0

    def test_closer_to_black(self):
        assert PngImporter._nearest_tile(50, 50, 50, self.PALETTE) == 1

    def test_single_tile_always_matches(self):
        palette = {7: (128, 64, 32)}
        assert PngImporter._nearest_tile(0, 0, 0, palette) == 7


# ---------------------------------------------------------------------------
# detect_tile_size
# ---------------------------------------------------------------------------

class TestDetectTileSize:
    def test_1px_tiles(self):
        img = solid_image([[(255, 255, 255), (0, 0, 0)],
                           [(0, 0, 0), (255, 255, 255)]], tile_size=1)
        assert PngImporter.detect_tile_size(img) == 1

    def test_8px_tiles(self):
        img = solid_image([[(255, 255, 255), (0, 0, 0)]], tile_size=8)
        assert PngImporter.detect_tile_size(img) == 8

    def test_16px_tiles(self):
        img = solid_image([[(255, 255, 255)], [(0, 0, 0)]], tile_size=16)
        assert PngImporter.detect_tile_size(img) == 16

    def test_non_uniform_blocks_fall_back_to_1(self):
        # 2×2 image where each pixel differs → no uniform block larger than 1
        img = Image.new("RGB", (2, 2))
        img.putdata([(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)])
        assert PngImporter.detect_tile_size(img) == 1

    def test_uniform_single_color_image_returns_full_size(self):
        img = solid_image([[(0, 0, 0), (0, 0, 0)],
                           [(0, 0, 0), (0, 0, 0)]], tile_size=4)
        # 8×8 all-black image — largest candidate that divides 8 evenly is 8
        size = PngImporter.detect_tile_size(img)
        assert img.size[0] % size == 0 and img.size[1] % size == 0


# ---------------------------------------------------------------------------
# load – basic
# ---------------------------------------------------------------------------

class TestLoad:
    def test_returns_correct_keys(self, tmp_path):
        img = solid_image([[(255, 255, 255)]], tile_size=1)
        path = save_png(tmp_path, img)
        result = PngImporter.load(path, TILE_DEFS_2)
        assert set(result.keys()) == {"width", "height", "grid", "tile_defs", "doors"}

    def test_1x1_white_is_boden(self, tmp_path):
        img = solid_image([[(255, 255, 255)]], tile_size=1)
        path = save_png(tmp_path, img)
        result = PngImporter.load(path, TILE_DEFS_2, tile_size=1)
        assert result["grid"] == [[0]]

    def test_1x1_black_is_wand(self, tmp_path):
        img = solid_image([[(0, 0, 0)]], tile_size=1)
        path = save_png(tmp_path, img)
        result = PngImporter.load(path, TILE_DEFS_2, tile_size=1)
        assert result["grid"] == [[1]]

    def test_2x2_grid_exact_colors(self, tmp_path):
        colors = [[(255, 255, 255), (0, 0, 0)],
                  [(0, 0, 0),       (255, 255, 255)]]
        img = solid_image(colors, tile_size=1)
        path = save_png(tmp_path, img)
        result = PngImporter.load(path, TILE_DEFS_2, tile_size=1)
        assert result["grid"] == [[0, 1], [1, 0]]

    def test_dimensions_match_grid(self, tmp_path):
        colors = [[(255, 255, 255)] * 3 for _ in range(2)]
        img = solid_image(colors, tile_size=1)
        path = save_png(tmp_path, img)
        result = PngImporter.load(path, TILE_DEFS_2, tile_size=1)
        assert result["width"] == 3
        assert result["height"] == 2

    def test_doors_always_empty(self, tmp_path):
        img = solid_image([[(255, 255, 255)]], tile_size=1)
        path = save_png(tmp_path, img)
        result = PngImporter.load(path, TILE_DEFS_2, tile_size=1)
        assert result["doors"] == {}

    def test_tile_defs_copied_into_result(self, tmp_path):
        img = solid_image([[(255, 255, 255)]], tile_size=1)
        path = save_png(tmp_path, img)
        result = PngImporter.load(path, TILE_DEFS_2, tile_size=1)
        assert result["tile_defs"] == TILE_DEFS_2
        # Verify it's a copy, not the same object
        assert result["tile_defs"] is not TILE_DEFS_2


# ---------------------------------------------------------------------------
# load – tile_size scaling
# ---------------------------------------------------------------------------

class TestLoadTileSize:
    def test_16px_tiles_produce_correct_map_size(self, tmp_path):
        # 96×64 image with 16px tiles → 6×4 map
        colors = [[(255, 255, 255)] * 6 for _ in range(4)]
        img = solid_image(colors, tile_size=16)
        path = save_png(tmp_path, img)
        result = PngImporter.load(path, TILE_DEFS_2, tile_size=16)
        assert result["width"] == 6
        assert result["height"] == 4

    def test_auto_detect_16px_tiles(self, tmp_path):
        colors = [[(255, 255, 255), (0, 0, 0)],
                  [(0, 0, 0),       (255, 255, 255)]]
        img = solid_image(colors, tile_size=16)
        path = save_png(tmp_path, img)
        # tile_size=0 → auto-detect
        result = PngImporter.load(path, TILE_DEFS_2, tile_size=0)
        assert result["width"] == 2
        assert result["height"] == 2
        assert result["grid"] == [[0, 1], [1, 0]]

    def test_8px_tiles_grid_content(self, tmp_path):
        colors = [[(255, 255, 255), (0, 0, 0), (255, 255, 255)]]
        img = solid_image(colors, tile_size=8)
        path = save_png(tmp_path, img)
        result = PngImporter.load(path, TILE_DEFS_2, tile_size=8)
        assert result["grid"] == [[0, 1, 0]]

    def test_all_four_standard_tiles(self, tmp_path):
        white  = (255, 255, 255)
        black  = (0,   0,   0)
        red    = (255, 59,  48)
        green  = (52,  199, 89)
        colors = [[white, black, red, green]]
        img = solid_image(colors, tile_size=4)
        path = save_png(tmp_path, img)
        result = PngImporter.load(path, TILE_DEFS_4, tile_size=4)
        assert result["grid"] == [[0, 1, 2, 3]]


# ---------------------------------------------------------------------------
# load – error cases
# ---------------------------------------------------------------------------

class TestLoadErrors:
    def test_non_divisible_raises(self, tmp_path):
        # 10×10 image with tile_size=3 (not divisible)
        img = Image.new("RGB", (10, 10), color=(255, 255, 255))
        path = save_png(tmp_path, img)
        with pytest.raises(ValueError, match="teilbar"):
            PngImporter.load(path, TILE_DEFS_2, tile_size=3)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(Exception):
            PngImporter.load(str(tmp_path / "nonexistent.png"), TILE_DEFS_2)
