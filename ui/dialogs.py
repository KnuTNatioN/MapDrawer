import tkinter as tk
from tkinter import messagebox, ttk

from core.config import PRESET_TILE_ORDER, TILE_DEFS


def _center_on_screen(window: tk.Toplevel) -> None:
    """Position a Toplevel window in the centre of the primary screen."""
    window.update_idletasks()
    w = window.winfo_reqwidth()
    h = window.winfo_reqheight()
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    window.geometry(f"+{x}+{y}")


# ---------------------------------------------------------------------------
# Startup dialog
# ---------------------------------------------------------------------------

class StartupDialog(tk.Toplevel):
    """Initial choice: create a new map or load an existing one."""

    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent)
        self.title("2D Map Editor")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.result = None  # "new", "load", or None

        outer = ttk.Frame(self, padding=24)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text="2D Map Editor", font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))
        ttk.Button(outer, text="Neue Map erstellen",   width=26, command=self._on_new).pack(pady=5)
        ttk.Button(outer, text="Vorhandene Map laden", width=26, command=self._on_load).pack(pady=5)
        ttk.Button(outer, text="Abbrechen",            width=26, command=self._on_cancel).pack(pady=(14, 0))

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        _center_on_screen(self)
        self.wait_visibility()
        self.focus_set()

    def _on_new(self) -> None:
        self.result = "new"
        self.destroy()

    def _on_load(self) -> None:
        self.result = "load"
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()


# ---------------------------------------------------------------------------
# New map dialog
# ---------------------------------------------------------------------------

class NewMapDialog(tk.Toplevel):
    """Let the user choose dimensions, zoom, and fill tile for a new map."""

    def __init__(
        self,
        parent: tk.Tk,
        width: int = 32,
        height: int = 24,
        cell_size: int = 24,
    ) -> None:
        super().__init__(parent)
        self.title("Neue 2D-Map")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.result = None

        self.width_var     = tk.IntVar(value=width)
        self.height_var    = tk.IntVar(value=height)
        self.cell_size_var = tk.IntVar(value=cell_size)
        self.fill_var      = tk.IntVar(value=0)

        outer = ttk.Frame(self, padding=14)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text="Neue Map erstellen", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        ttk.Label(outer, text="Breite:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Spinbox(
            outer, from_=1, to=4096, textvariable=self.width_var, width=12,
        ).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(outer, text="Höhe:").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Spinbox(
            outer, from_=1, to=4096, textvariable=self.height_var, width=12,
        ).grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(outer, text="Start-Zoom:").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Combobox(
            outer,
            textvariable=self.cell_size_var,
            values=[8, 12, 16, 20, 24, 28, 32, 40, 48],
            state="readonly",
            width=10,
        ).grid(row=3, column=1, sticky="ew", pady=4)

        fill_frame = ttk.LabelFrame(outer, text="Startinhalt", padding=8)
        fill_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 10))
        for tile_id in PRESET_TILE_ORDER:
            ttk.Radiobutton(
                fill_frame,
                text=f"{TILE_DEFS[tile_id]['name']} ({tile_id})",
                value=tile_id,
                variable=self.fill_var,
            ).pack(anchor="w")

        button_row = ttk.Frame(outer)
        button_row.grid(row=5, column=0, columnspan=2, sticky="e", pady=(4, 0))
        ttk.Button(button_row, text="Abbrechen", command=self._on_cancel).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(button_row, text="Erstellen",  command=self._on_ok).pack(side=tk.RIGHT)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        _center_on_screen(self)
        self.wait_visibility()
        self.focus_set()

    def _on_ok(self) -> None:
        width     = self.width_var.get()
        height    = self.height_var.get()
        cell_size = self.cell_size_var.get()
        if width < 1 or height < 1:
            messagebox.showerror(
                "Ungültige Größe",
                "Breite und Höhe müssen größer als 0 sein.",
                parent=self,
            )
            return
        self.result = {
            "width":     width,
            "height":    height,
            "cell_size": max(4, min(64, int(cell_size))),
            "fill_tile": int(self.fill_var.get()),
        }
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()


# ---------------------------------------------------------------------------
# Door-ID dialog
# ---------------------------------------------------------------------------

class DoorIdDialog(tk.Toplevel):
    """Edit the numeric ID attached to a door tile."""

    def __init__(self, parent: tk.Tk, current_id: int) -> None:
        super().__init__(parent)
        self.title("Tür-ID bearbeiten")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.result = None

        self.var = tk.StringVar(value=str(current_id))
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text="Tür-ID:").pack(anchor="w")
        entry = ttk.Entry(outer, textvariable=self.var)
        entry.pack(fill=tk.X, pady=(4, 10))
        entry.focus_set()

        buttons = ttk.Frame(outer)
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="Abbrechen", command=self.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(buttons, text="OK",        command=self._on_ok).pack(side=tk.RIGHT)
        self.bind("<Return>", lambda _e: self._on_ok())
        _center_on_screen(self)

    def _on_ok(self) -> None:
        try:
            value = int(self.var.get().strip())
            if value < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Ungültige Eingabe",
                "Bitte eine ganze Zahl >= 0 eingeben.",
                parent=self,
            )
            return
        self.result = value
        self.destroy()


# ---------------------------------------------------------------------------
# Resize map dialog
# ---------------------------------------------------------------------------

class ResizeMapDialog(tk.Toplevel):
    """Let the user resize an existing map with anchor selection and fill tile."""

    def __init__(
        self,
        parent: tk.Tk,
        current_width: int,
        current_height: int,
    ) -> None:
        super().__init__(parent)
        self.title("Map-Größe ändern")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.result = None

        self._orig_width  = current_width
        self._orig_height = current_height

        self.width_var  = tk.IntVar(value=current_width)
        self.height_var = tk.IntVar(value=current_height)
        self.anchor_var = tk.StringVar(value="nw")
        self.fill_var   = tk.IntVar(value=0)

        style = ttk.Style()
        style.configure("Warning.TLabel", foreground="red")

        outer = ttk.Frame(self, padding=14)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text="Map-Größe ändern", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        ttk.Label(outer, text="Neue Breite:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Spinbox(
            outer, from_=1, to=4096, textvariable=self.width_var, width=12,
        ).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(outer, text="Neue Höhe:").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Spinbox(
            outer, from_=1, to=4096, textvariable=self.height_var, width=12,
        ).grid(row=2, column=1, sticky="ew", pady=4)

        anchor_frame = ttk.LabelFrame(outer, text="Ankerpunkt", padding=8)
        anchor_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 4))
        for i, (sym, val) in enumerate([
            ("↖", "nw"), ("↑", "n"),  ("↗", "ne"),
            ("←", "w"),  ("·", "c"),  ("→", "e"),
            ("↙", "sw"), ("↓", "s"),  ("↘", "se"),
        ]):
            ttk.Radiobutton(
                anchor_frame, text=sym, value=val, variable=self.anchor_var,
            ).grid(row=i // 3, column=i % 3, padx=10, pady=4)

        fill_frame = ttk.LabelFrame(outer, text="Füll-Kachel (neue Zellen)", padding=8)
        fill_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(4, 4))
        for tile_id in PRESET_TILE_ORDER:
            ttk.Radiobutton(
                fill_frame,
                text=f"{TILE_DEFS[tile_id]['name']} ({tile_id})",
                value=tile_id,
                variable=self.fill_var,
            ).pack(anchor="w")

        self._warn_lbl = ttk.Label(outer, text="", style="Warning.TLabel", wraplength=260)
        self._warn_lbl.grid(row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))

        button_row = ttk.Frame(outer)
        button_row.grid(row=6, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(button_row, text="Abbrechen", command=self._on_cancel).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(button_row, text="Anwenden",  command=self._on_ok).pack(side=tk.RIGHT)

        self.width_var.trace_add("write",  lambda *_: self._update_warning())
        self.height_var.trace_add("write", lambda *_: self._update_warning())

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        _center_on_screen(self)
        self.wait_visibility()
        self.focus_set()

    def _update_warning(self) -> None:
        try:
            w = self.width_var.get()
            h = self.height_var.get()
        except tk.TclError:
            self._warn_lbl.config(text="")
            return
        if w < self._orig_width or h < self._orig_height:
            self._warn_lbl.config(text="Daten außerhalb der neuen Grenzen gehen verloren.")
        else:
            self._warn_lbl.config(text="")

    def _on_ok(self) -> None:
        try:
            width  = self.width_var.get()
            height = self.height_var.get()
        except tk.TclError:
            messagebox.showerror("Ungültige Eingabe", "Bitte gültige Zahlen eingeben.", parent=self)
            return
        if width < 1 or height < 1:
            messagebox.showerror(
                "Ungültige Größe",
                "Breite und Höhe müssen größer als 0 sein.",
                parent=self,
            )
            return
        self.result = {
            "width":     width,
            "height":    height,
            "anchor":    self.anchor_var.get(),
            "fill_tile": self.fill_var.get(),
        }
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()
