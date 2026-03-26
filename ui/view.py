import math
import pathlib
import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional, Tuple

from core.config import (
    DEFAULT_CELL_SIZE,
    GRID_COLOR,
    MAX_CELL_SIZE,
    MIN_CELL_SIZE,
    PRESET_TILE_ORDER,
    PREVIEW_COLOR,
)

# ── Design tokens ──────────────────────────────────────────────────────────────
_BG        = "#f3f3f3"   # app / toolbar background
_BG_PANEL  = "#fafafa"   # left panel background
_BG_TOOL   = "#f0f0f0"   # tool / tile-row normal background
_BG_SEL    = "#ddeeff"   # selected tool / tile-row background
_BG_CANVAS = "#d4d4d4"   # canvas surround (gray mat like Paint)
_BD_NORM   = "#d0d0d0"   # normal border / separator
_BD_ACT    = "#0078d4"   # active selection border (Windows blue)
_FG_TEXT   = "#1a1a1a"   # regular text
_FG_HINT   = "#999999"   # secondary / disabled hint text
_FG_SEC    = "#5a5a5a"   # section label text

_FONT_UI   = ("Segoe UI", 10)
_FONT_BOLD = ("Segoe UI", 10, "bold")
_FONT_SEC  = ("Segoe UI", 8, "bold")
_FONT_SML  = ("Segoe UI", 9)


# ── FontAwesome setup ──────────────────────────────────────────────────────────
# Needs: pip install fontawesome Pillow
# OR:    place fa-solid-900.ttf in a fonts/ folder next to main.py

_FA_TTF: Optional[pathlib.Path] = None
_FA_PHOTOS: Dict = {}  # PhotoImage cache – prevents garbage-collection

# Font Awesome 5 Free Solid – unicode codepoints
_FA = {
    "file":           "\uf15b",
    "folder-open":    "\uf07c",
    "save":           "\uf0c7",
    "file-export":    "\uf56e",
    "undo":           "\uf0e2",
    "redo":           "\uf01e",
    "power-off":      "\uf011",
    "pencil-alt":     "\uf303",
    "fill-drip":      "\uf576",
    "circle":         "\uf111",
    "ruler-combined": "\uf546",
    "door-open":      "\uf52b",
}


def _woff2_to_ttf(woff2: pathlib.Path) -> Optional[pathlib.Path]:
    """Convert a .woff2 file to .ttf (same folder) using fonttools+brotli.

    Returns the .ttf path on success, None otherwise.
    Requires: pip install fonttools brotli
    """
    ttf = woff2.with_suffix(".ttf")
    if ttf.exists():
        return ttf
    try:
        from fontTools.ttLib import TTFont  # type: ignore
        font = TTFont(str(woff2))
        font.save(str(ttf))
        return ttf
    except Exception:
        return None


def _init_fontawesome() -> None:
    global _FA_TTF
    fonts_dir = pathlib.Path(__file__).parent.parent / "fonts"

    # 1. Ready-made TTF in local fonts/ folder
    ttf = fonts_dir / "fa-solid-900.ttf"
    if ttf.exists():
        _FA_TTF = ttf

    # 2. woff2 in local fonts/ folder → auto-convert to TTF
    if _FA_TTF is None:
        woff2 = fonts_dir / "fa-solid-900.woff2"
        if woff2.exists():
            _FA_TTF = _woff2_to_ttf(woff2)

    # 3. Try via `fontawesome` pip package
    if _FA_TTF is None:
        try:
            import fontawesome as _fa_pkg  # type: ignore
            base = pathlib.Path(_fa_pkg.__file__).parent
            for rel in ("fonts/fa-solid-900.ttf", "fa-solid-900.ttf"):
                cand = base / rel
                if cand.exists():
                    _FA_TTF = cand
                    break
        except ImportError:
            pass

    # Register with Windows GDI so the font name is known (best-effort)
    if _FA_TTF is not None:
        try:
            import ctypes
            ctypes.windll.gdi32.AddFontResourceExW(str(_FA_TTF), 0x10, 0)
        except Exception:
            pass


_init_fontawesome()


def _fa_photo(icon: str, size: int = 14, fg: str = _FG_TEXT):
    """Render a FontAwesome icon as a cached PhotoImage via Pillow.

    Returns None if the FA TTF or Pillow is unavailable.
    """
    char = _FA.get(icon)
    if char is None or _FA_TTF is None:
        return None
    key = (icon, size, fg)
    if key in _FA_PHOTOS:
        return _FA_PHOTOS[key]
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageTk  # type: ignore
        sz = size + 4
        img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        fnt = ImageFont.truetype(str(_FA_TTF), size)
        bbox = draw.textbbox((0, 0), char, font=fnt)
        x = (sz - (bbox[2] - bbox[0])) // 2 - bbox[0]
        y = (sz - (bbox[3] - bbox[1])) // 2 - bbox[1]
        draw.text((x, y), char, fill=fg, font=fnt)
        photo = ImageTk.PhotoImage(img)
        _FA_PHOTOS[key] = photo
        return photo
    except Exception:
        return None


# ── Module-level widget helpers ────────────────────────────────────────────────

def _tb_sep(parent: tk.Frame) -> None:
    """Vertical separator for the top toolbar."""
    tk.Frame(parent, width=1, bg=_BD_NORM).pack(
        side=tk.LEFT, fill=tk.Y, padx=6, pady=4
    )


def _section_label(parent: tk.Widget, text: str) -> None:
    """All-caps section header inside the left panel."""
    tk.Label(
        parent, text=text,
        bg=_BG_PANEL, fg=_FG_SEC, font=_FONT_SEC,
        anchor="w", padx=10,
    ).pack(fill=tk.X, pady=(10, 2))


def _panel_sep(parent: tk.Widget) -> None:
    """Horizontal rule inside the left panel."""
    tk.Frame(parent, height=1, bg=_BD_NORM).pack(fill=tk.X, padx=0, pady=2)


def _tool_button(
    parent: tk.Widget,
    icon: str,
    label: str,
    command,
    fallback_emoji: str = "",
) -> tk.Button:
    """Flat, full-width tool button for the left panel with optional FA icon."""
    photo = _fa_photo(icon, size=14)
    if photo:
        text = f"  {label}"
    elif fallback_emoji:
        text = f"{fallback_emoji}  {label}"
    else:
        text = label
    btn = tk.Button(
        parent,
        text=text,
        font=_FONT_UI,
        anchor="w", padx=8 if photo else 12,
        bg=_BG_TOOL, fg=_FG_TEXT,
        activebackground="#e0eeff",
        activeforeground=_FG_TEXT,
        relief=tk.FLAT, bd=0,
        highlightthickness=1,
        highlightbackground=_BD_NORM,
        cursor="hand2",
        command=command,
    )
    if photo:
        btn.config(image=photo, compound=tk.LEFT)
        btn._fa_photo = photo  # type: ignore[attr-defined]
    btn.pack(fill=tk.X, padx=6, pady=2, ipady=4)
    return btn


# ── MapView ────────────────────────────────────────────────────────────────────

class MapView:
    """All tkinter widgets and canvas drawing.

    Layout:
      ┌─────────────────────────────────────────────┐
      │  Toolbar  (Neu · Öffnen · Speichern · …)    │
      ├─────────┬───────────────────────────────────┤
      │         │                                   │
      │  Panel  │   Canvas  (scrollable)            │
      │  Tools  │                                   │
      │  Tiles  │                                   │
      │  Door   │                                   │
      │  View   │                                   │
      ├─────────┴───────────────────────────────────┤
      │  Status bar  (zoom slider · info text)      │
      └─────────────────────────────────────────────┘
    """

    def __init__(self, root: tk.Tk, controller) -> None:
        self.root        = root
        self.controller  = controller
        self._cell_size  = DEFAULT_CELL_SIZE

        # ── tk variables ──────────────────────────────────────────────────
        self.active_tile       = tk.IntVar(value=1)
        self.fill_mode         = tk.BooleanVar(value=False)
        self.circle_mode       = tk.BooleanVar(value=False)
        self.show_grid         = tk.BooleanVar(value=True)
        self.door_id_var       = tk.StringVar(value="1")
        self.status_var        = tk.StringVar()
        self.selected_info_var = tk.StringVar()

        # ── internal refs for dynamic updates ─────────────────────────────
        self._tool_btns: Dict[str, tk.Button] = {}
        self._tile_rows: Dict[int, tk.Frame]  = {}

        # Auto-refresh tool / tile visuals on variable changes
        self.fill_mode.trace_add("write",  lambda *_: self._refresh_tool_buttons())
        self.circle_mode.trace_add("write", lambda *_: self._refresh_tool_buttons())
        self.active_tile.trace_add("write", lambda *_: self._refresh_tile_rows())

        self._build_ui()

    # ── cell_size ──────────────────────────────────────────────────────────────

    @property
    def cell_size(self) -> int:
        return self._cell_size

    def set_cell_size(self, value: int) -> None:
        self._cell_size = max(MIN_CELL_SIZE, min(MAX_CELL_SIZE, int(value)))
        self.zoom_scale.set(self._cell_size)
        self._zoom_label.config(text=f"{self._cell_size}px")

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        c    = self.controller
        root = self.root
        root.configure(bg=_BG)

        # ── Toolbar ──────────────────────────────────────────────────────────
        toolbar = tk.Frame(root, bg=_BG, padx=6, pady=6)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        for text, icon, cmd in [
            ("Neu",             "file",        c.new_map),
            ("Öffnen",          "folder-open", c.open_map),
            ("Speichern",       "save",        c.save_map),
            ("Speichern unter", "file-export", lambda: c.save_map(save_as=True)),
        ]:
            photo = _fa_photo(icon, size=12)
            btn = ttk.Button(toolbar, text=text, command=cmd)
            if photo:
                btn.config(image=photo, compound=tk.LEFT)
                btn._fa_photo = photo  # type: ignore[attr-defined]
            btn.pack(side=tk.LEFT, padx=(0, 2))

        _tb_sep(toolbar)

        for icon, fallback, cmd in [
            ("undo", "↩", c.undo),
            ("redo", "↪", c.redo),
        ]:
            photo = _fa_photo(icon, size=12)
            btn = ttk.Button(toolbar, command=cmd)
            if photo:
                btn.config(image=photo)
                btn._fa_photo = photo  # type: ignore[attr-defined]
            else:
                btn.config(text=fallback, width=3)
            btn.pack(side=tk.LEFT, padx=(0, 2))

        _tb_sep(toolbar)

        photo = _fa_photo("power-off", size=12)
        btn = ttk.Button(toolbar, text="Beenden", command=root.quit)
        if photo:
            btn.config(image=photo, compound=tk.LEFT)
            btn._fa_photo = photo  # type: ignore[attr-defined]
        btn.pack(side=tk.LEFT)

        # Separator line under toolbar
        tk.Frame(root, height=1, bg=_BD_NORM).pack(fill=tk.X)

        # ── Status bar (packed before body so BOTTOM takes effect) ───────────
        statusbar = tk.Frame(root, bg=_BG, pady=5)
        statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Frame(root, height=1, bg=_BD_NORM).pack(side=tk.BOTTOM, fill=tk.X)

        tk.Label(statusbar, text="Zoom:", bg=_BG, fg=_FG_TEXT, font=_FONT_SML).pack(
            side=tk.LEFT, padx=(10, 4)
        )
        self.zoom_scale = ttk.Scale(
            statusbar,
            from_=MIN_CELL_SIZE, to=MAX_CELL_SIZE, length=110,
            command=lambda v: c.on_zoom_scale(v),
        )
        self.zoom_scale.set(self._cell_size)
        self.zoom_scale.pack(side=tk.LEFT)
        self._zoom_label = tk.Label(
            statusbar, text=f"{self._cell_size}px", width=5,
            bg=_BG, fg=_FG_HINT, font=_FONT_SML,
        )
        self._zoom_label.pack(side=tk.LEFT, padx=(2, 6))

        tk.Frame(statusbar, width=1, bg=_BD_NORM).pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=2)

        tk.Label(
            statusbar, textvariable=self.status_var,
            bg=_BG, fg=_FG_TEXT, font=_FONT_SML, anchor="w",
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 10))

        # ── Main body ─────────────────────────────────────────────────────────
        body = tk.Frame(root, bg=_BG)
        body.pack(fill=tk.BOTH, expand=True)

        # ── Left panel ────────────────────────────────────────────────────────
        panel = tk.Frame(body, bg=_BG_PANEL, width=186)
        panel.pack(side=tk.LEFT, fill=tk.Y)
        panel.pack_propagate(False)

        # Right border of panel
        tk.Frame(body, width=1, bg=_BD_NORM).pack(side=tk.LEFT, fill=tk.Y)

        # ·· Tools section ··
        _section_label(panel, "WERKZEUGE")

        self._tool_btns["pencil"] = _tool_button(
            panel, "pencil-alt", "Pinsel", lambda: c.select_tool("pencil"),
            fallback_emoji="🖋️",
        )
        self._tool_btns["fill"] = _tool_button(
            panel, "fill-drip", "Füllen", lambda: c.select_tool("fill"),
            fallback_emoji="🧺",
        )
        self._tool_btns["circle"] = _tool_button(
            panel, "circle", "Kreis", lambda: c.select_tool("circle"),
            fallback_emoji="⭕",
        )
        _line_photo = _fa_photo("ruler-combined", size=13, fg=_FG_HINT)
        _line_lbl = tk.Label(
            panel,
            text="  Linie  (Shift + Ziehen)" if _line_photo else "📐  Linie  (Shift + Ziehen)",
            bg=_BG_PANEL, fg=_FG_HINT, font=_FONT_SML,
            anchor="w", padx=8 if _line_photo else 22,
        )
        if _line_photo:
            _line_lbl.config(image=_line_photo, compound=tk.LEFT)
            _line_lbl._fa_photo = _line_photo  # type: ignore[attr-defined]
        _line_lbl.pack(fill=tk.X, pady=(2, 4))

        _panel_sep(panel)

        # ·· Tile palette section ··
        _section_label(panel, "KACHELN")
        self._palette_frame = tk.Frame(panel, bg=_BG_PANEL)
        self._palette_frame.pack(fill=tk.X, padx=6, pady=(0, 4))

        _panel_sep(panel)

        # ·· Door-ID section ··
        _section_label(panel, "TÜR-ID")
        door_inner = tk.Frame(panel, bg=_BG_PANEL)
        door_inner.pack(fill=tk.X, padx=8, pady=(0, 4))
        ttk.Entry(door_inner, textvariable=self.door_id_var).pack(fill=tk.X, pady=(0, 4))
        _door_photo = _fa_photo("door-open", size=12)
        _door_btn = ttk.Button(
            door_inner, text="An Zelle zuweisen",
            command=c.assign_door_id_to_current_cell,
        )
        if _door_photo:
            _door_btn.config(image=_door_photo, compound=tk.LEFT)
            _door_btn._fa_photo = _door_photo  # type: ignore[attr-defined]
        _door_btn.pack(fill=tk.X)

        _panel_sep(panel)

        # ·· View toggles section ··
        _section_label(panel, "ANSICHT")
        ttk.Checkbutton(
            panel, text="Gitter anzeigen",
            variable=self.show_grid,
            command=c.on_grid_toggle,
        ).pack(anchor="w", padx=10, pady=(0, 4))

        _panel_sep(panel)

        # ·· Active cell info ··
        _section_label(panel, "AKTIVE ZELLE")
        tk.Label(
            panel,
            textvariable=self.selected_info_var,
            bg=_BG_PANEL, fg=_FG_TEXT, font=_FONT_SML,
            justify="left", wraplength=166, anchor="nw",
        ).pack(anchor="w", padx=10, pady=(0, 6))

        # ── Canvas area ───────────────────────────────────────────────────────
        canvas_outer = tk.Frame(body, bg=_BG_CANVAS)
        canvas_outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        canvas_holder = tk.Frame(canvas_outer, bg=_BG_CANVAS)
        canvas_holder.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            canvas_holder,
            bg="#ffffff",
            highlightthickness=0,
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        yscroll = ttk.Scrollbar(canvas_holder, orient=tk.VERTICAL,   command=self.canvas.yview)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        xscroll = ttk.Scrollbar(canvas_outer,  orient=tk.HORIZONTAL, command=self.canvas.xview)
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)

        # ── Canvas bindings ───────────────────────────────────────────────────
        self.canvas.bind("<Button-1>",        c.on_left_down)
        self.canvas.bind("<B1-Motion>",       c.on_drag)
        self.canvas.bind("<ButtonRelease-1>", c.on_mouse_up)
        self.canvas.bind("<Button-3>",        c.on_right_down)
        self.canvas.bind("<B3-Motion>",       c.on_drag)
        self.canvas.bind("<ButtonRelease-3>", c.on_mouse_up)
        self.canvas.bind("<Motion>",          c.on_motion)
        self.canvas.bind("<Double-Button-1>", c.on_double_click)
        self.canvas.bind("<MouseWheel>",      c.on_mouse_wheel)
        self.canvas.bind("<Button-4>",        lambda _e: c.adjust_zoom(2))
        self.canvas.bind("<Button-5>",        lambda _e: c.adjust_zoom(-2))

        # ── Keyboard shortcuts ────────────────────────────────────────────────
        root.bind("<Control-n>", lambda _e: c.new_map())
        root.bind("<Control-o>", lambda _e: c.open_map())
        root.bind("<Control-s>", lambda _e: c.save_map())
        root.bind("<Control-z>", lambda _e: c.undo())
        root.bind("<Control-y>", lambda _e: c.redo())
        root.bind("<Control-Z>", lambda _e: c.redo())
        root.bind("<g>",         lambda _e: c.on_grid_key())
        root.bind("<f>",         lambda _e: c.select_tool("fill"))
        root.bind("<k>",         lambda _e: c.select_tool("circle"))

        self._refresh_tool_buttons()

    # ── Tool-button visuals ────────────────────────────────────────────────────

    def _refresh_tool_buttons(self, *_) -> None:
        pencil_active = not self.fill_mode.get() and not self.circle_mode.get()
        states = {
            "pencil": pencil_active,
            "fill":   self.fill_mode.get(),
            "circle": self.circle_mode.get(),
        }
        for name, active in states.items():
            btn = self._tool_btns.get(name)
            if btn is None:
                continue
            if active:
                btn.config(
                    bg=_BG_SEL,
                    font=_FONT_BOLD,
                    highlightbackground=_BD_ACT,
                    highlightthickness=2,
                )
            else:
                btn.config(
                    bg=_BG_TOOL,
                    font=_FONT_UI,
                    highlightbackground=_BD_NORM,
                    highlightthickness=1,
                )

    # ── Tile palette ───────────────────────────────────────────────────────────

    def build_palette(self, tile_defs: dict) -> None:
        """Rebuild the tile palette from current tile definitions."""
        for w in self._palette_frame.winfo_children():
            w.destroy()
        self._tile_rows.clear()

        for tile_id in PRESET_TILE_ORDER:
            info = tile_defs.get(tile_id)
            if info is None:
                continue
            row = tk.Frame(
                self._palette_frame,
                bg=_BG_TOOL,
                highlightthickness=1,
                highlightbackground=_BD_NORM,
                cursor="hand2",
            )
            row.pack(fill=tk.X, pady=2)

            swatch = tk.Canvas(
                row, width=26, height=26,
                bg=info["color"],
                highlightthickness=0,
            )
            swatch.pack(side=tk.LEFT, padx=(6, 8), pady=5)

            name_lbl = tk.Label(
                row, text=info["name"],
                bg=_BG_TOOL, fg=_FG_TEXT, font=_FONT_UI, anchor="w",
            )
            name_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

            tid = tile_id
            row._labels = [name_lbl]     # type: ignore[attr-defined]
            row._swatch  = swatch        # type: ignore[attr-defined]

            for widget in (row, name_lbl, swatch):
                widget.bind("<Button-1>", lambda _e, t=tid: self._select_tile(t))

            self._tile_rows[tile_id] = row

        self._refresh_tile_rows()

    def _select_tile(self, tile_id: int) -> None:
        self.active_tile.set(tile_id)
        self.controller.update_selected_info()

    def _refresh_tile_rows(self, *_) -> None:
        active = self.active_tile.get()
        for tile_id, row in self._tile_rows.items():
            labels = getattr(row, "_labels", [])
            if tile_id == active:
                row.config(bg=_BG_SEL, highlightbackground=_BD_ACT, highlightthickness=2)
                for lbl in labels:
                    lbl.config(bg=_BG_SEL)
            else:
                row.config(bg=_BG_TOOL, highlightbackground=_BD_NORM, highlightthickness=1)
                for lbl in labels:
                    lbl.config(bg=_BG_TOOL)

    # ── Canvas drawing ─────────────────────────────────────────────────────────

    def redraw_canvas(self, model) -> None:
        if not model.grid:
            return
        self.canvas.delete("all")
        w_px = model.width  * self._cell_size
        h_px = model.height * self._cell_size
        self.canvas.configure(scrollregion=(0, 0, w_px, h_px))
        outline = GRID_COLOR if self.show_grid.get() else ""
        for y in range(model.height):
            for x in range(model.width):
                self._draw_cell(model, x, y, outline)

    def redraw_cell(self, model, x: int, y: int) -> None:
        self.canvas.delete(f"cell_{x}_{y}")
        self.canvas.delete(f"overlay_{x}_{y}")
        outline = GRID_COLOR if self.show_grid.get() else ""
        self._draw_cell(model, x, y, outline)

    def _draw_cell(self, model, x: int, y: int, outline: str) -> None:
        tile_id = model.grid[y][x]
        color = model.tile_defs.get(tile_id, {"color": "#ff00ff"})["color"]
        x1 = x * self._cell_size
        y1 = y * self._cell_size
        x2 = x1 + self._cell_size
        y2 = y1 + self._cell_size
        self.canvas.create_rectangle(
            x1, y1, x2, y2, fill=color, outline=outline, tags=f"cell_{x}_{y}"
        )
        if tile_id == 2 and (x, y) in model.doors:
            self._draw_door_label(x, y, model.doors[(x, y)])
        elif tile_id == 3:
            self._draw_spawn_marker(x, y)

    def _draw_door_label(self, x: int, y: int, door_id: int) -> None:
        cx, cy = self.cell_center(x, y)
        self.canvas.create_text(
            cx, cy,
            text=str(door_id),
            fill="#ffffff",
            font=("Segoe UI", max(8, self._cell_size // 3), "bold"),
            tags=f"overlay_{x}_{y}",
        )

    def _draw_spawn_marker(self, x: int, y: int) -> None:
        pad = max(2, self._cell_size // 5)
        x1 = x * self._cell_size + pad
        y1 = y * self._cell_size + pad
        x2 = (x + 1) * self._cell_size - pad
        y2 = (y + 1) * self._cell_size - pad
        w = max(1, self._cell_size // 8)
        self.canvas.create_line(x1, y1, x2, y2, fill="#ffffff", width=w, tags=f"overlay_{x}_{y}")
        self.canvas.create_line(x1, y2, x2, y1, fill="#ffffff", width=w, tags=f"overlay_{x}_{y}")

    # ── Preview drawing ────────────────────────────────────────────────────────

    def clear_preview(self) -> None:
        self.canvas.delete("preview")

    def draw_preview_line(self, sx: int, sy: int, ex: int, ey: int) -> None:
        self.clear_preview()
        x1, y1 = self.cell_center(sx, sy)
        x2, y2 = self.cell_center(ex, ey)
        self.canvas.create_line(
            x1, y1, x2, y2,
            fill=PREVIEW_COLOR, dash=(5, 3),
            width=max(1, self._cell_size // 6),
            tags="preview",
        )

    def draw_preview_circle(self, sx: int, sy: int, ex: int, ey: int) -> None:
        self.clear_preview()
        r = round(math.hypot(ex - sx, ey - sy))
        if r <= 0:
            return
        pcx, pcy = self.cell_center(sx, sy)
        r_px = r * self._cell_size
        self.canvas.create_oval(
            pcx - r_px, pcy - r_px, pcx + r_px, pcy + r_px,
            outline=PREVIEW_COLOR, dash=(5, 3),
            width=max(1, self._cell_size // 6),
            tags="preview",
        )

    # ── Coordinate helpers ─────────────────────────────────────────────────────

    def cell_from_event(self, event) -> Tuple[int, int]:
        x = int(self.canvas.canvasx(event.x)) // self._cell_size
        y = int(self.canvas.canvasy(event.y)) // self._cell_size
        return x, y

    def cell_center(self, x: int, y: int) -> Tuple[int, int]:
        half = self._cell_size // 2
        return x * self._cell_size + half, y * self._cell_size + half

    # ── UI update helpers ──────────────────────────────────────────────────────

    def update_title(self, file_path: Optional[str], model, mode_name: str) -> None:
        filename = file_path if file_path else "Unbenannt"
        self.root.title(
            f"2D Map Editor – {filename}  "
            f"({model.width}×{model.height}, Zoom {self._cell_size}, {mode_name})"
        )

    def update_status(
        self,
        x: int,
        y: int,
        in_bounds: bool,
        model,
        mode_name: str,
        line_hint: bool,
    ) -> None:
        if in_bounds:
            tile_id   = model.grid[y][x]
            tile_name = model.tile_defs.get(tile_id, {}).get("name", f"Unbekannt ({tile_id})")
            extra = (
                f"  |  Tür-ID: {model.doors[(x, y)]}"
                if tile_id == 2 and (x, y) in model.doors
                else ""
            )
            hint = "  |  Linie" if line_hint else ""
            self.status_var.set(
                f"({x}, {y})  |  {tile_name}{extra}"
                f"  |  Zoom {self._cell_size}px  |  {mode_name}{hint}"
            )
        else:
            self.status_var.set(f"Außerhalb der Map  |  Zoom {self._cell_size}px")

    def update_selected_info(
        self, model, x: Optional[int] = None, y: Optional[int] = None
    ) -> None:
        tile_id = self.active_tile.get()
        tile    = model.tile_defs.get(tile_id, {})
        text = [
            f"{tile.get('name', '?')} ({tile_id})",
            f"Farbe: {tile.get('color', '?')}",
            f"Begehbar: {'ja' if tile.get('walkable') else 'nein'}",
        ]
        if tile_id == 2:
            text.append(f"Tür-ID: {self.door_id_var.get().strip() or '0'}")
        if x is not None and y is not None and model.in_bounds(x, y):
            current      = model.grid[y][x]
            current_tile = model.tile_defs.get(current, {})
            text.append("")
            text.append(f"Zelle ({x}, {y}): {current_tile.get('name', '?')}")
            if current == 2 and (x, y) in model.doors:
                text.append(f"Tür-ID: {model.doors[(x, y)]}")
        self.selected_info_var.set("\n".join(text))
