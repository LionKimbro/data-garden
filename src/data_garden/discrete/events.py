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

def selection_clear():
    selection_set([], None)

def selection_has(nid):
    return nid in workspace["selection"]["ids"]

def selection_single(nid):
    if nid:
        selection_set([nid], nid)
    else:
        selection_clear()
