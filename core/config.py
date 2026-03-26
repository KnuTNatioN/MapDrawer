# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

MAGIC = b"2dM1"
VERSION = 1
DEFAULT_EXT = ".2dm"

TILE_DEFS = {
    0: {"name": "Boden",  "color": "#ffffff", "walkable": True,  "needs_extra": False},
    1: {"name": "Wand",   "color": "#000000", "walkable": False, "needs_extra": False},
    2: {"name": "Tür",    "color": "#ff3b30", "walkable": True,  "needs_extra": True},
    3: {"name": "Spawn",  "color": "#34c759", "walkable": True,  "needs_extra": False},
}

PRESET_TILE_ORDER = [0, 1, 2, 3]

PREVIEW_COLOR = "#007aff"
GRID_COLOR    = "#d0d0d0"

MAX_UNDO = 50

MIN_CELL_SIZE     = 6
MAX_CELL_SIZE     = 64
DEFAULT_CELL_SIZE = 24

DEFAULT_MAP_WIDTH  = 32
DEFAULT_MAP_HEIGHT = 24
