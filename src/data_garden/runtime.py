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

# -----------------------
# MAIN
# -----------------------

def main():
    root = tk.Tk()
    widgets["root"] = root

    try:
        root.tk.call("tk", "scaling", 1.25)
    except Exception:
        pass

    ttk.Style(root)
    build_ui()
    bind_events()
    refresh_projection()
    root.mainloop()

