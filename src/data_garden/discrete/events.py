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
# DISCRETE: EVENTS
# -----------------------

def emit_event(event):
    events.append(event)

def selection_ids():
    return list(workspace["selection"]["ids"])

def selection_primary():
    return workspace["selection"]["primary"]

def selection_set(ids, primary=None):
    clean = []
    for nid in ids:
        if nid and nid not in clean:
            clean.append(nid)
    if primary not in clean:
        if clean:
            primary = clean[0]
        else:
            primary = None
    workspace["selection"]["ids"][:] = clean
    workspace["selection"]["primary"] = primary

def manipulation_show(kind="size"):
    workspace["manipulation"]["kind"] = kind
    workspace["manipulation"]["visible"] = bool(selection_ids())

def manipulation_hide():
    workspace["manipulation"]["visible"] = False

def manipulation_toggle():
    if not selection_ids():
        manipulation_hide()
        return
    if workspace["manipulation"]["kind"] == "size":
        manipulation_show("rotate")
    else:
        manipulation_show("size")

def selection_clear():
    selection_set([], None)

def selection_has(nid):
    return nid in workspace["selection"]["ids"]

def selection_single(nid):
    if nid:
        selection_set([nid], nid)
    else:
        selection_clear()
