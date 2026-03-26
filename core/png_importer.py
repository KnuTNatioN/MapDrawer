from typing import Dict, Optional, Tuple

from PIL import Image

from .config import TILE_DEFS

# Tile sizes to try during auto-detection, largest first.
_CANDIDATE_SIZES = [64, 48, 32, 24, 16, 12, 8, 4, 2, 1]


class PngImporter:
    """Convert a PNG image into a 2dm map payload dict.

    The returned dict is compatible with MapModel.load_payload() and
    TwoDMapCodec.save().

    Color matching uses nearest-neighbor in RGB space (squared Euclidean
    distance).  Door metadata cannot be encoded in a PNG, so the resulting
    doors dict is always empty.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hex_to_rgb(color: str) -> Tuple[int, int, int]:
        color = color.lstrip("#")
        return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)

    @staticmethod
    def _nearest_tile(
        r: int, g: int, b: int, palette: Dict[int, Tuple[int, int, int]]
    ) -> int:
        """Return the tile_id whose color is closest to (r, g, b)."""
        best_id = next(iter(palette))
        best_dist = float("inf")
        for tile_id, (tr, tg, tb) in palette.items():
            dist = (r - tr) ** 2 + (g - tg) ** 2 + (b - tb) ** 2
            if dist < best_dist:
                best_dist = dist
                best_id = tile_id
        return best_id

    @classmethod
    def _block_is_uniform(
        cls, img: Image.Image, x0: int, y0: int, size: int
    ) -> bool:
        """Return True if every pixel in the (size×size) block is identical."""
        colors = img.crop((x0, y0, x0 + size, y0 + size)).getcolors(maxcolors=2)
        return colors is not None and len(colors) == 1

    # ------------------------------------------------------------------
    # Auto-detection
    # ------------------------------------------------------------------

    @classmethod
    def detect_tile_size(cls, img: Image.Image) -> int:
        """Return the largest N where every N×N pixel block is a uniform color.

        Falls back to 1 (one pixel per tile) if no larger size works.
        """
        w, h = img.size
        for size in _CANDIDATE_SIZES:
            if w % size != 0 or h % size != 0:
                continue
            if all(
                cls._block_is_uniform(img, tx * size, ty * size, size)
                for ty in range(h // size)
                for tx in range(w // size)
            ):
                return size
        return 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def load(
        cls,
        path: str,
        tile_defs: Optional[Dict[int, dict]] = None,
        tile_size: int = 0,
    ) -> dict:
        """Load a PNG and return a map payload dict.

        Parameters
        ----------
        path:
            Path to the PNG file.
        tile_defs:
            Tile definitions used for color matching.  Defaults to the
            standard TILE_DEFS from config.
        tile_size:
            Pixels per tile edge.  Pass 0 (default) to auto-detect.

        Returns
        -------
        dict with keys: width, height, grid, tile_defs, doors
        """
        if tile_defs is None:
            tile_defs = TILE_DEFS

        img = Image.open(path).convert("RGB")
        w, h = img.size

        if tile_size == 0:
            tile_size = cls.detect_tile_size(img)

        if w % tile_size != 0 or h % tile_size != 0:
            raise ValueError(
                f"Bildgröße {w}×{h} px ist nicht durch Tile-Größe {tile_size} teilbar."
            )

        map_w = w // tile_size
        map_h = h // tile_size

        palette: Dict[int, Tuple[int, int, int]] = {
            tile_id: cls._hex_to_rgb(info["color"])
            for tile_id, info in tile_defs.items()
        }

        pixels = img.load()
        half = max(tile_size // 2, 0)

        grid = []
        for ty in range(map_h):
            row = []
            for tx in range(map_w):
                cx = tx * tile_size + half
                cy = ty * tile_size + half
                r, g, b = pixels[cx, cy]
                row.append(cls._nearest_tile(r, g, b, palette))
            grid.append(row)

        return {
            "width": map_w,
            "height": map_h,
            "grid": grid,
            "tile_defs": {tid: dict(info) for tid, info in tile_defs.items()},
            "doors": {},
        }
