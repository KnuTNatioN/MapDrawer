import copy
import math
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional, Tuple

from core.codec import TwoDMapCodec
from core.config import (
    DEFAULT_EXT,
    DEFAULT_MAP_HEIGHT,
    DEFAULT_MAP_WIDTH,
    MAX_CELL_SIZE,
    MIN_CELL_SIZE,
    TILE_DEFS,
)
from core.model import MapModel
from .dialogs import DoorIdDialog, NewMapDialog, ResizeMapDialog
from .view import MapView


class MapController:
    """Wires MapModel and MapView together.

    Owns all event handlers, file operations, and interaction state
    (line/circle drawing in progress, is_painting flag, etc.).
    """

    def __init__(self, root: tk.Tk) -> None:
        self.root  = root
        self.model = MapModel()
        self.view  = MapView(root, self)

        self.file_path: Optional[str] = None

        # Interaction state
        self.is_painting:       bool = False
        self.current_paint_tile: int = 1
        self.line_start:   Optional[Tuple[int, int, int]] = None
        self.circle_start: Optional[Tuple[int, int, int, bool]] = None
        self.rect_start:   Optional[Tuple[int, int, int, bool]] = None
        self._alt_held:    bool = False

        # Track Alt key reliably (event.state is inconsistent on Windows)
        for key in ("<Alt_L>", "<Alt_R>"):
            root.bind(key, lambda _e: self._set_alt(True), add="+")
        for key in ("<KeyRelease-Alt_L>", "<KeyRelease-Alt_R>"):
            root.bind(key, lambda _e: self._set_alt(False), add="+")

    # ------------------------------------------------------------------
    # Mode helpers
    # ------------------------------------------------------------------

    def _active_mode_name(self) -> str:
        if self.view.circle_mode.get():
            return "Kreis"
        if self.view.rect_mode.get():
            return "Rechteck"
        if self.view.fill_mode.get():
            return "Füllen"
        return "Malen"

    def select_tool(self, tool: str) -> None:
        """Switch active tool: 'pencil', 'fill', 'circle', or 'rect'.

        Pressing the same tool a second time toggles back to pencil.
        """
        if tool == "fill"   and self.view.fill_mode.get():
            tool = "pencil"
        if tool == "circle" and self.view.circle_mode.get():
            tool = "pencil"
        if tool == "rect"   and self.view.rect_mode.get():
            tool = "pencil"
        self.view.fill_mode.set(tool == "fill")
        self.view.circle_mode.set(tool == "circle")
        self.view.rect_mode.set(tool == "rect")
        self.view.update_title(self.file_path, self.model, self._active_mode_name())

    # kept for any external callers
    def on_fill_mode_toggle(self) -> None:
        self.select_tool("fill")

    def on_circle_mode_toggle(self) -> None:
        self.select_tool("circle")

    def on_grid_toggle(self) -> None:
        self.view.redraw_canvas(self.model)

    def on_grid_key(self) -> None:
        self.view.show_grid.set(not self.view.show_grid.get())
        self.view.redraw_canvas(self.model)

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------

    def on_zoom_scale(self, value: str) -> None:
        self.set_zoom(int(float(value)))

    def set_zoom(self, value: int) -> None:
        value = max(MIN_CELL_SIZE, min(MAX_CELL_SIZE, int(value)))
        if value == self.view.cell_size:
            return
        self.view.set_cell_size(value)
        self.view.redraw_canvas(self.model)
        self.view.update_title(self.file_path, self.model, self._active_mode_name())

    def adjust_zoom(self, delta: int) -> None:
        self.set_zoom(self.view.cell_size + delta)

    def on_mouse_wheel(self, event) -> None:
        self.adjust_zoom(2 if event.delta > 0 else -2)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def new_map(self) -> bool:
        dlg = NewMapDialog(
            self.root,
            self.model.width  or DEFAULT_MAP_WIDTH,
            self.model.height or DEFAULT_MAP_HEIGHT,
            self.view.cell_size,
        )
        self.root.wait_window(dlg)
        if dlg.result is None:
            return False
        params = dlg.result
        self.model.initialise(
            params["width"], params["height"], params["fill_tile"], TILE_DEFS
        )
        self.view.set_cell_size(params["cell_size"])
        self.file_path = None
        self.view.build_palette(self.model.tile_defs)
        self.view.redraw_canvas(self.model)
        self.view.update_selected_info(self.model)
        self.view.update_title(self.file_path, self.model, self._active_mode_name())
        return True

    def open_map(self) -> None:
        path = filedialog.askopenfilename(
            title="2D-Map öffnen",
            filetypes=[("2D Map Dateien", "*.2dm"), ("Alle Dateien", "*.*")],
        )
        if not path:
            return
        try:
            payload = TwoDMapCodec.load(path)
            self.model.load_payload(payload)
            self.file_path = path
            self.view.build_palette(self.model.tile_defs)
            self.view.redraw_canvas(self.model)
            self.view.update_selected_info(self.model)
            self.view.update_title(self.file_path, self.model, self._active_mode_name())
        except Exception as exc:
            messagebox.showerror("Fehler beim Öffnen", str(exc), parent=self.root)

    def save_map(self, save_as: bool = False) -> None:
        path = self.file_path
        if save_as or not path:
            path = filedialog.asksaveasfilename(
                title="2D-Map speichern",
                defaultextension=DEFAULT_EXT,
                filetypes=[("2D Map Dateien", "*.2dm"), ("Alle Dateien", "*.*")],
                initialfile="map.2dm",
            )
            if not path:
                return
        try:
            self.model.validate_before_save()
            TwoDMapCodec.save(
                path,
                self.model.width,
                self.model.height,
                self.model.grid,
                self.model.tile_defs,
                self.model.doors,
            )
            self.file_path = path
            self.view.update_title(self.file_path, self.model, self._active_mode_name())
            messagebox.showinfo(
                "Gespeichert", "Map wurde erfolgreich gespeichert.", parent=self.root
            )
        except Exception as exc:
            messagebox.showerror("Fehler beim Speichern", str(exc), parent=self.root)

    # ------------------------------------------------------------------
    # Map resize
    # ------------------------------------------------------------------

    def resize_map(self) -> None:
        dlg = ResizeMapDialog(self.root, self.model.width, self.model.height)
        self.root.wait_window(dlg)
        if dlg.result is None:
            return
        params = dlg.result
        snapshot = (
            "resize",
            self.model.width,
            self.model.height,
            copy.deepcopy(self.model.grid),
            dict(self.model.doors),
        )
        self.model._push_undo([snapshot], clear_redo=True)
        self.model.resize(params["width"], params["height"], params["anchor"], params["fill_tile"])
        self.view.redraw_canvas(self.model)
        self.view.update_title(self.file_path, self.model, self._active_mode_name())

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------

    def undo(self) -> None:
        changes = self.model.pop_undo()
        if changes is None:
            return
        if changes[0][0] == "resize":
            _, old_w, old_h, old_grid, old_doors = changes[0]
            redo_snap = (
                "resize",
                self.model.width,
                self.model.height,
                copy.deepcopy(self.model.grid),
                dict(self.model.doors),
            )
            self.model.push_redo([redo_snap])
            self.model.width  = old_w
            self.model.height = old_h
            self.model.grid   = old_grid
            self.model.doors  = old_doors
            self.view.redraw_canvas(self.model)
            self.view.update_title(self.file_path, self.model, self._active_mode_name())
        else:
            affected = self.model.apply_changes(changes, reverse=True)
            self.model.push_redo(changes)
            for x, y in affected:
                self.view.redraw_cell(self.model, x, y)

    def redo(self) -> None:
        changes = self.model.pop_redo()
        if changes is None:
            return
        if changes[0][0] == "resize":
            _, new_w, new_h, new_grid, new_doors = changes[0]
            undo_snap = (
                "resize",
                self.model.width,
                self.model.height,
                copy.deepcopy(self.model.grid),
                dict(self.model.doors),
            )
            self.model._push_undo([undo_snap], clear_redo=False)
            self.model.width  = new_w
            self.model.height = new_h
            self.model.grid   = new_grid
            self.model.doors  = new_doors
            self.view.redraw_canvas(self.model)
            self.view.update_title(self.file_path, self.model, self._active_mode_name())
        else:
            affected = self.model.apply_changes(changes, reverse=False)
            self.model.redo_to_undo(changes)
            for x, y in affected:
                self.view.redraw_cell(self.model, x, y)

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def on_left_down(self, event) -> None:
        self._start_paint(event, self.view.active_tile.get())

    def on_right_down(self, event) -> None:
        self._start_paint(event, 0)  # right-click erases to floor (tile 0)

    def _start_paint(self, event, tile_id: int) -> None:
        self.is_painting       = True
        self.current_paint_tile = tile_id
        x, y = self.view.cell_from_event(event)
        if not self.model.in_bounds(x, y):
            return

        self.model.begin_action()

        if self.view.circle_mode.get():
            self.circle_start = (x, y, tile_id, self._rect_modifier_active())
            return

        if self.view.rect_mode.get():
            centered = self._rect_modifier_active()
            self.rect_start = (x, y, tile_id, centered)
            self.view.draw_preview_rect(x, y, x, y, centered)
            return

        if self._line_modifier_active(event):
            self.line_start = (x, y, tile_id)
            self.view.draw_preview_line(x, y, x, y)
            return

        if self.view.fill_mode.get():
            door_id = self._parse_door_id(default=0)
            if door_id is None:
                return
            modified = self.model.flood_fill(x, y, tile_id, door_id if tile_id == 2 else None)
            for cx, cy in modified:
                self.view.redraw_cell(self.model, cx, cy)
            self.model.commit_action()
            return

        self._paint_tile(x, y, tile_id)
        self.view.update_selected_info(self.model, x, y)

    def on_drag(self, event) -> None:
        if not self.is_painting:
            return
        x, y = self.view.cell_from_event(event)
        if not self.model.in_bounds(x, y):
            return

        if self.circle_start is not None:
            sx, sy, _, centered = self.circle_start
            self.view.draw_preview_circle(sx, sy, x, y, centered)
            return

        if self.rect_start is not None:
            sx, sy, _, centered = self.rect_start
            self.view.draw_preview_rect(sx, sy, x, y, centered)
            return

        if self.line_start is not None:
            sx, sy, _ = self.line_start
            self.view.draw_preview_line(sx, sy, x, y)
            return

        if self.view.fill_mode.get():
            return

        self._paint_tile(x, y, self.current_paint_tile)
        self.view.update_selected_info(self.model, x, y)

    def on_mouse_up(self, event) -> None:
        x, y = self.view.cell_from_event(event)

        if self.circle_start is not None:
            if self.model.in_bounds(x, y):
                sx, sy, tile_id, centered = self.circle_start
                if centered:
                    r = round(math.hypot(x - sx, y - sy))
                    for px, py in self.model.midpoint_circle(sx, sy, r):
                        self._paint_tile(px, py, tile_id)
                else:
                    fcx = (sx + x) / 2
                    fcy = (sy + y) / 2
                    r = round(math.hypot(x - fcx, y - fcy))
                    for px, py in self.model.midpoint_circle(round(fcx), round(fcy), r):
                        self._paint_tile(px, py, tile_id)
            self.view.clear_preview()
            self.circle_start = None

        elif self.rect_start is not None:
            if self.model.in_bounds(x, y):
                sx, sy, tile_id, centered = self.rect_start
                if centered:
                    hw = abs(x - sx)
                    hh = abs(y - sy)
                    for cx, cy in self.model.rect_outline(sx - hw, sy - hh, sx + hw, sy + hh):
                        self._paint_tile(cx, cy, tile_id)
                else:
                    for cx, cy in self.model.rect_outline(sx, sy, x, y):
                        self._paint_tile(cx, cy, tile_id)
            self.view.clear_preview()
            self.rect_start = None

        elif self.line_start is not None:
            if self.model.in_bounds(x, y):
                sx, sy, tile_id = self.line_start
                for cx, cy in self.model.bresenham(sx, sy, x, y):
                    self._paint_tile(cx, cy, tile_id)
            self.view.clear_preview()
            self.line_start = None

        self.model.commit_action()
        self.is_painting = False

    def on_motion(self, event) -> None:
        x, y = self.view.cell_from_event(event)
        in_bounds = self.model.in_bounds(x, y)
        line_hint = (
            not self.view.circle_mode.get()
            and not self.view.fill_mode.get()
            and not self.view.rect_mode.get()
            and self._line_modifier_active(event)
        )
        self.view.update_status(
            x, y, in_bounds, self.model, self._active_mode_name(), line_hint
        )

        if self.is_painting and in_bounds:
            if self.circle_start is not None:
                sx, sy, _, centered = self.circle_start
                self.view.draw_preview_circle(sx, sy, x, y, centered)
            elif self.rect_start is not None:
                sx, sy, _, centered = self.rect_start
                self.view.draw_preview_rect(sx, sy, x, y, centered)
            elif self.line_start is not None:
                sx, sy, _ = self.line_start
                self.view.draw_preview_line(sx, sy, x, y)

    def on_double_click(self, event) -> None:
        x, y = self.view.cell_from_event(event)
        if not self.model.in_bounds(x, y):
            return
        if self.model.grid[y][x] != 2:
            return
        old_door = self.model.doors.get((x, y), 0)
        dlg = DoorIdDialog(self.root, old_door)
        self.root.wait_window(dlg)
        if dlg.result is None or dlg.result == old_door:
            return
        self.model.push_undo([(x, y, 2, 2, old_door, dlg.result)])
        self.model.doors[(x, y)] = dlg.result
        self.view.redraw_cell(self.model, x, y)
        self.view.update_selected_info(self.model, x, y)

    # ------------------------------------------------------------------
    # Tile painting (single cell)
    # ------------------------------------------------------------------

    def _paint_tile(self, x: int, y: int, tile_id: int) -> None:
        if not self.model.in_bounds(x, y):
            return
        if tile_id not in self.model.tile_defs:
            return
        # Skip if unchanged (except door tiles that may need a new ID assigned)
        if (
            self.model.grid[y][x] == tile_id
            and not (tile_id == 2 and (x, y) not in self.model.doors)
        ):
            return

        self.model.record_before(x, y)
        door_id: Optional[int] = None
        if tile_id == 2:
            door_id = self._parse_door_id(default=None)
            if door_id is None and (x, y) not in self.model.doors:
                door_id = 0
        self.model.set_tile(x, y, tile_id, door_id)
        self.view.redraw_cell(self.model, x, y)

    # ------------------------------------------------------------------
    # Door helpers
    # ------------------------------------------------------------------

    def assign_door_id_to_current_cell(self) -> None:
        x, y = self._cell_under_pointer()
        if x is None:
            messagebox.showinfo(
                "Keine Zelle gewählt",
                "Bewege die Maus über eine Tür-Zelle und klicke dann erneut.",
                parent=self.root,
            )
            return
        if self.model.grid[y][x] != 2:
            messagebox.showinfo(
                "Keine Tür",
                "Unter dem Mauszeiger liegt keine Tür-Zelle.",
                parent=self.root,
            )
            return
        door_id = self._parse_door_id(default=0)
        if door_id is None:
            return
        old_door = self.model.doors.get((x, y))
        self.model.push_undo([(x, y, 2, 2, old_door, door_id)])
        self.model.doors[(x, y)] = door_id
        self.view.redraw_cell(self.model, x, y)
        self.view.update_selected_info(self.model, x, y)

    def _parse_door_id(self, default: Optional[int] = 0) -> Optional[int]:
        raw = self.view.door_id_var.get().strip()
        if raw == "":
            return default
        try:
            value = int(raw)
        except ValueError:
            messagebox.showerror(
                "Ungültige Tür-ID",
                "Die Tür-ID muss eine ganze Zahl sein.",
                parent=self.root,
            )
            return None
        if value < 0:
            messagebox.showerror(
                "Ungültige Tür-ID",
                "Die Tür-ID muss >= 0 sein.",
                parent=self.root,
            )
            return None
        return value

    def _cell_under_pointer(self) -> Tuple[Optional[int], Optional[int]]:
        try:
            px = self.view.canvas.winfo_pointerx() - self.view.canvas.winfo_rootx()
            py = self.view.canvas.winfo_pointery() - self.view.canvas.winfo_rooty()
        except tk.TclError:
            return None, None
        event_like = type("E", (), {"x": px, "y": py})
        x, y = self.view.cell_from_event(event_like)
        if not self.model.in_bounds(x, y):
            return None, None
        return x, y

    # ------------------------------------------------------------------
    # Info panel shortcut (called by view palette radio buttons)
    # ------------------------------------------------------------------

    def update_selected_info(
        self, x: Optional[int] = None, y: Optional[int] = None
    ) -> None:
        self.view.update_selected_info(self.model, x, y)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _line_modifier_active(event) -> bool:
        return bool(event.state & 0x0001) or bool(event.state & 0x0004)

    def _set_alt(self, state: bool) -> None:
        self._alt_held = state

    def _rect_modifier_active(self) -> bool:
        return self._alt_held
