import json
import math
import os
import shutil
import tempfile
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox

from data_garden.constants import *
from data_garden.state import *

# -----------------------
# RUNTIME
# -----------------------

def pump_events():
    while events:
        event = events.pop(0)
        reduce_event(event)
        while effects:
            effect = effects.pop(0)
            route_effect(effect)

def request_shutdown():
    g["shutdown_requested"] = True

def complete_shutdown_if_requested():
    if not g["shutdown_requested"]:
        return
    if g["shutdown_scheduled"]:
        return
    root = widgets.get("root")
    if not root:
        return
    g["shutdown_scheduled"] = True
    try:
        root.after_idle(root.destroy)
    except Exception:
        root.destroy()

# -----------------------
# MAIN
# -----------------------

def main(firstload=None):
    root = tk.Tk()
    widgets["root"] = root

    try:
        root.tk.call("tk", "scaling", 1.25)
    except Exception:
        pass

    ttk.Style(root)
    build_ui()
    bind_events()
    if firstload:
        load_project_from_path(firstload)
    refresh_projection()
    root.mainloop()

