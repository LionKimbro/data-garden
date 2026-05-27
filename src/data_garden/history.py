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
# HISTORY MANAGER
# -----------------------

def undo_history():
    emit_event({"type": "UNDO"})
    pump_events()
    refresh_projection()

def redo_history():
    emit_event({"type": "REDO"})
    pump_events()
    refresh_projection()

def remember_current(label):
    remember_snapshot(snapshot_state(), label)

def remember_snapshot(snapshot, label):
    if g["restoring_history"]:
        return
    snapshot["label"] = label
    history["undo"].append(snapshot)
    history["redo"].clear()
    trim_history()

def trim_history():
    limit = history["limit"]
    while len(history["undo"]) > limit:
        history["undo"].pop(0)

def restore_undo():
    if not history["undo"]:
        effects.append({"type": "STATUS", "text": "Nothing to undo"})
        return
    snapshot = history["undo"].pop()
    label = snapshot.get("label", "change")
    current = snapshot_state()
    current["label"] = label
    history["redo"].append(current)
    restore_snapshot(snapshot)
    effects.append({"type": "INSPECTOR_REFRESH"})
    effects.append({"type": "STATUS", "text": "Undid " + label})

def restore_redo():
    if not history["redo"]:
        effects.append({"type": "STATUS", "text": "Nothing to redo"})
        return
    snapshot = history["redo"].pop()
    label = snapshot.get("label", "change")
    current = snapshot_state()
    current["label"] = label
    history["undo"].append(current)
    restore_snapshot(snapshot)
    effects.append({"type": "INSPECTOR_REFRESH"})
    effects.append({"type": "STATUS", "text": "Redid " + label})

def snapshot_state():
    return {
        "workspace": snapshot_workspace(),
        "world_revision_guid": world["current_revision_guid"],
    }

def snapshot_workspace():
    return {
        "mode": workspace["mode"],
        "awaiting_click_for": workspace["awaiting_click_for"],
        "camera": {
            "scale": workspace["camera"]["scale"],
            "ox": workspace["camera"]["ox"],
            "oy": workspace["camera"]["oy"],
        },
    }

def restore_snapshot(snapshot):
    g["restoring_history"] = True
    try:
        live_ids = selection_ids()
        live_primary = selection_primary()
        workspace["mode"] = snapshot["workspace"]["mode"]
        workspace["awaiting_click_for"] = snapshot["workspace"]["awaiting_click_for"]
        workspace["camera"]["scale"] = snapshot["workspace"]["camera"]["scale"]
        workspace["camera"]["ox"] = snapshot["workspace"]["camera"]["ox"]
        workspace["camera"]["oy"] = snapshot["workspace"]["camera"]["oy"]

        goto_world_revision(snapshot["world_revision_guid"])

        reconcile_selection(live_ids, live_primary)
        reset_continuity_for_time_jump()
    finally:
        g["restoring_history"] = False

def reconcile_selection(ids, primary):
    valid = existing_ids(ids)
    if primary not in valid:
        if valid:
            primary = valid[-1]
        else:
            primary = None
    selection_set(valid, primary)

def reset_continuity_for_time_jump():
    derived.clear()
    tokenizer_state["drag_anchor_sx"] = raw["current"]["sx"]
    tokenizer_state["drag_anchor_sy"] = raw["current"]["sy"]
    judge_clear()
    reset_chord_organism()
    reset_drag_selection_organism()
    reset_rotate_selection_organism()
    reset_size_selection_organism()
    reset_camera_organisms()
    reset_marquee_organism()

def clear_history():
    history["undo"].clear()
    history["redo"].clear()
