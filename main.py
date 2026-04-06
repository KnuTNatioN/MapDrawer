import tkinter as tk
from tkinter import ttk

from ui.controller import MapController
from ui.dialogs import StartupDialog


def main() -> None:
    root = tk.Tk()
    root.title("2D Map Editor")
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    w, h = 1400, 860
    x = (sw - w) // 2
    y = (sh - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")
    ttk.Style(root).theme_use("clam")

    # Build the editor UI first so the root window exists –
    # required for Toplevel transient dialogs to render correctly on Windows.
    app = MapController(root)

    dlg = StartupDialog(root)
    root.wait_window(dlg)

    if dlg.result is None:
        root.destroy()
        return

    if dlg.result == "load":
        app.open_map()
        if not app.file_path:
            if not app.new_map():
                root.destroy()
                return
    else:
        if not app.new_map():
            root.destroy()
            return

    root.mainloop()


if __name__ == "__main__":
    main()
