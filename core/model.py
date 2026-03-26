from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .config import MAX_UNDO


@dataclass
class DoorEntry:
    x: int
    y: int
    door_id: int


class MapModel:
    """Pure data model – no tkinter, no UI logic."""

    def __init__(self) -> None:
        self.width: int = 0
        self.height: int = 0
        self.grid: List[List[int]] = []
        self.tile_defs: Dict[int, dict] = {}
        self.doors: Dict[Tuple[int, int], int] = {}

        self.undo_stack: List[list] = []
        self.redo_stack: List[list] = []
        self._cell_before: Dict[Tuple[int, int], Tuple[int, Optional[int]]] = {}

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def initialise(
        self,
        width: int,
        height: int,
        fill_tile: int,
        tile_defs: Dict[int, dict],
    ) -> None:
        self.width = width
        self.height = height
        self.grid = [[fill_tile] * width for _ in range(height)]
        self.tile_defs = {tid: dict(info) for tid, info in tile_defs.items()}
        self.doors.clear()
        self.clear_undo_redo()

    def load_payload(self, payload: dict) -> None:
        self.width     = payload["width"]
        self.height    = payload["height"]
        self.grid      = payload["grid"]
        self.tile_defs = payload["tile_defs"]
        self.doors     = payload["doors"]
        self.clear_undo_redo()

    # ------------------------------------------------------------------
    # Bounds
    # ------------------------------------------------------------------

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------

    def begin_action(self) -> None:
        """Start recording cells for one undoable action."""
        self._cell_before = {}

    def record_before(self, x: int, y: int) -> None:
        """Snapshot a cell before modification (only the first time per action)."""
        if (x, y) not in self._cell_before:
            self._cell_before[(x, y)] = (self.grid[y][x], self.doors.get((x, y)))

    def commit_action(self) -> bool:
        """Finalise the current action and push it onto the undo stack.

        Returns True if any cell actually changed.
        """
        if not self._cell_before:
            return False
        changes = []
        for (x, y), (old_tile, old_door) in self._cell_before.items():
            new_tile = self.grid[y][x]
            new_door = self.doors.get((x, y))
            if old_tile != new_tile or old_door != new_door:
                changes.append((x, y, old_tile, new_tile, old_door, new_door))
        self._cell_before = {}
        if not changes:
            return False
        self._push_undo(changes, clear_redo=True)
        return True

    def push_undo(self, changes: list) -> None:
        """Push a ready-made change record onto the undo stack and clear redo."""
        self._push_undo(changes, clear_redo=True)

    def _push_undo(self, changes: list, clear_redo: bool) -> None:
        self.undo_stack.append(changes)
        if len(self.undo_stack) > MAX_UNDO:
            self.undo_stack.pop(0)
        if clear_redo:
            self.redo_stack.clear()

    def pop_undo(self) -> Optional[list]:
        return self.undo_stack.pop() if self.undo_stack else None

    def push_redo(self, changes: list) -> None:
        self.redo_stack.append(changes)

    def pop_redo(self) -> Optional[list]:
        return self.redo_stack.pop() if self.redo_stack else None

    def redo_to_undo(self, changes: list) -> None:
        """Move a redo entry back to the undo stack without clearing redo."""
        self._push_undo(changes, clear_redo=False)

    def clear_undo_redo(self) -> None:
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._cell_before = {}

    # ------------------------------------------------------------------
    # Tile operations
    # ------------------------------------------------------------------

    def set_tile(
        self, x: int, y: int, tile_id: int, door_id: Optional[int] = None
    ) -> None:
        """Set a tile and manage its door entry. Does NOT record undo."""
        self.grid[y][x] = tile_id
        if tile_id == 2:
            if door_id is not None:
                self.doors[(x, y)] = door_id
            elif (x, y) not in self.doors:
                self.doors[(x, y)] = 0
        else:
            self.doors.pop((x, y), None)

    def apply_changes(
        self, changes: list, reverse: bool
    ) -> List[Tuple[int, int]]:
        """Apply a change record list. Returns the list of (x, y) cells modified."""
        affected: List[Tuple[int, int]] = []
        for x, y, old_tile, new_tile, old_door, new_door in changes:
            tile = old_tile if reverse else new_tile
            door = old_door if reverse else new_door
            self.grid[y][x] = tile
            if door is not None:
                self.doors[(x, y)] = door
            else:
                self.doors.pop((x, y), None)
            affected.append((x, y))
        return affected

    def flood_fill(
        self,
        start_x: int,
        start_y: int,
        tile_id: int,
        door_id: Optional[int] = None,
    ) -> List[Tuple[int, int]]:
        """BFS flood fill. Returns list of (x, y) cells that were modified."""
        if not self.in_bounds(start_x, start_y):
            return []
        target = self.grid[start_y][start_x]
        if target == tile_id:
            return []
        modified: List[Tuple[int, int]] = []
        q = deque([(start_x, start_y)])
        while q:
            x, y = q.popleft()
            if not self.in_bounds(x, y) or self.grid[y][x] != target:
                continue
            self.record_before(x, y)
            self.set_tile(x, y, tile_id, door_id)
            modified.append((x, y))
            q.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
        return modified

    def validate_before_save(self) -> None:
        for (x, y), door_id in self.doors.items():
            if not self.in_bounds(x, y):
                raise ValueError(f"Tür-Eintrag außerhalb der Map: ({x}, {y})")
            if self.grid[y][x] != 2:
                raise ValueError(
                    f"Für Tür-ID {door_id} existiert keine Tür-Zelle an ({x}, {y})."
                )
            if door_id < 0:
                raise ValueError("Tür-IDs müssen >= 0 sein.")

    # ------------------------------------------------------------------
    # Drawing algorithms (pure math, no tkinter)
    # ------------------------------------------------------------------

    @staticmethod
    def bresenham(x0: int, y0: int, x1: int, y1: int):
        """Yield (x, y) grid cells along the line from (x0, y0) to (x1, y1)."""
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            yield x0, y0
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def rect_outline(
        self, x1: int, y1: int, x2: int, y2: int
    ) -> List[Tuple[int, int]]:
        """Return in-bounds grid cells on the perimeter of a rectangle."""
        lx, rx = min(x1, x2), max(x1, x2)
        ty, by = min(y1, y2), max(y1, y2)
        cells: set = set()
        for x in range(lx, rx + 1):
            if self.in_bounds(x, ty):
                cells.add((x, ty))
            if self.in_bounds(x, by):
                cells.add((x, by))
        for y in range(ty, by + 1):
            if self.in_bounds(lx, y):
                cells.add((lx, y))
            if self.in_bounds(rx, y):
                cells.add((rx, y))
        return list(cells)

    def midpoint_circle(
        self, cx: int, cy: int, r: int
    ) -> List[Tuple[int, int]]:
        """Return in-bounds grid cells on the circumference of a circle."""
        if r <= 0:
            return [(cx, cy)] if self.in_bounds(cx, cy) else []
        cells: set = set()
        x, y, err = r, 0, 1 - r
        while x >= y:
            for gx, gy in [
                (cx + x, cy + y), (cx - x, cy + y),
                (cx + x, cy - y), (cx - x, cy - y),
                (cx + y, cy + x), (cx - y, cy + x),
                (cx + y, cy - x), (cx - y, cy - x),
            ]:
                if self.in_bounds(gx, gy):
                    cells.add((gx, gy))
            y += 1
            if err < 0:
                err += 2 * y + 1
            else:
                x -= 1
                err += 2 * (y - x) + 1
        return list(cells)
