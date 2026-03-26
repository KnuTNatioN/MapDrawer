import tkinter as tk
from tkinter import ttk

from ui.controller import MapController
from ui.dialogs import StartupDialog


def main() -> None:
    root = tk.Tk()
    root.title("2D Map Editor")
    root.geometry("1400x860")
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
