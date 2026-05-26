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
# INSPECTOR
# -----------------------

def refresh_inspector():
    if "var_id" not in widgets:
        return
    nid = selection_primary()
    if not nid:
        widgets["var_id"].set("")
        widgets["var_kind"].set("")
        widgets["var_title"].set("")
        widgets["var_url"].set("")
        widgets["var_fill"].set("#6d4c41")
        widgets["var_w"].set(140)
        widgets["var_h"].set(100)
        widgets["var_angle"].set(0)
        widgets["txt_note"].delete("1.0", tk.END)
        return

    node = find_node(nid)
    if not node:
        return

    widgets["var_id"].set(node["id"])
    widgets["var_kind"].set(node["kind"])
    widgets["var_title"].set(node["title"])
    widgets["var_url"].set(node["url"])
    widgets["var_fill"].set(node["fill"])
    widgets["var_w"].set(node["w"])
    widgets["var_h"].set(node["h"])
    widgets["var_angle"].set(node["angle"])
    widgets["txt_note"].delete("1.0", tk.END)
    widgets["txt_note"].insert("1.0", node["note"])

def apply_inspector():
    nid = selection_primary()
    if not nid:
        return
    fields = {
        "title": widgets["var_title"].get(),
        "url": widgets["var_url"].get(),
        "fill": widgets["var_fill"].get(),
        "w": float(widgets["var_w"].get()),
        "h": float(widgets["var_h"].get()),
        "angle": float(widgets["var_angle"].get()),
        "note": widgets["txt_note"].get("1.0", tk.END).rstrip(),
    }
    emit_event({"type": "UPDATE_NODE", "id": nid, "fields": fields})
    pump_events()
    refresh_projection()
    status_set("Applied changes to " + nid)

def pick_color():
    nid = selection_primary()
    if not nid:
        return
    emit_event({"type": "COMMAND_ENTERED", "code": "CO"})
    pump_events()
    refresh_projection()

def open_link():
    nid = selection_primary()
    if not nid:
        return
    emit_event({"type": "OPEN_LINK", "id": nid})
    pump_events()

def delete_selected():
    nid = selection_primary()
    if not nid:
        return
    emit_event({"type": "COMMAND_ENTERED", "code": "DO"})
    pump_events()
    refresh_projection()

def clone_selected():
    nid = selection_primary()
    if not nid:
        return
    emit_event({"type": "COMMAND_ENTERED", "code": "XO"})
    pump_events()
    refresh_projection()

def status_set(text):
    if "status" not in widgets:
        return
    widgets["status"].config(text=text)
