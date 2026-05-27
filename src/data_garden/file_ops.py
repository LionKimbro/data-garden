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
# FILE OPS
# -----------------------

def file_new():
    if not confirm_discard():
        return
    emit_event({"type": "NEW_PROJECT"})
    pump_events()
    refresh_projection()

def file_open():
    path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All", "*.*")])
    if not path:
        return
    load_project_from_path(path)

def load_project_from_path(path):
    try:
        data = read_json(path)
    except Exception as err:
        messagebox.showerror("Open failed", str(err))
        return
    emit_event({"type": "LOAD_PROJECT", "data": data})
    pump_events()
    g["filepath"] = str(path)
    status_set("Opened " + os.path.basename(str(path)))
    refresh_projection()

def file_save():
    if not g["filepath"]:
        return file_save_as()
    try:
        atomic_write_json(g["filepath"], dump_project())
        status_set("Saved " + os.path.basename(g["filepath"]))
    except Exception as err:
        messagebox.showerror("Save failed", str(err))

def file_save_as():
    path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
    if not path:
        return
    g["filepath"] = path
    file_save()

def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)

def dump_project():
    return {
        "version": 1,
        "nodes": [copy_node(node) for node in world["nodes"]],
        "camera": {
            "scale": workspace["camera"]["scale"],
            "ox": workspace["camera"]["ox"],
            "oy": workspace["camera"]["oy"],
        },
        "next_id": world["next_id"],
    }

def load_world(data):
    world["nodes"].clear()
    world["next_id"] = 1

    for raw_node in data.get("nodes", []):
        world["nodes"].append(normalize_node(raw_node))

    if "next_id" in data:
        world["next_id"] = int(data["next_id"])
    repair_next_id()

def load_camera(data):
    camera = data.get("camera", {})
    workspace["camera"]["scale"] = float(camera.get("scale", 1.0))
    workspace["camera"]["ox"] = float(camera.get("ox", 0.0))
    workspace["camera"]["oy"] = float(camera.get("oy", 0.0))

def normalize_node(raw_node):
    kind = raw_node.get("kind", "rect")
    nid = raw_node.get("id")
    if not nid:
        nid = gen_id()
    w = raw_node.get("w", 140)
    h = raw_node.get("h", 100)
    fill = raw_node.get("fill", "#6d4c41")
    if kind == "circle":
        w = raw_node.get("w", 120)
        h = raw_node.get("h", 120)
        fill = raw_node.get("fill", "#3a6ea5")

    return {
        "id": nid,
        "kind": kind,
        "x": float(raw_node.get("x", 0.0)),
        "y": float(raw_node.get("y", 0.0)),
        "w": float(w),
        "h": float(h),
        "angle": float(raw_node.get("angle", 0.0)),
        "fill": fill,
        "title": raw_node.get("title", ""),
        "url": raw_node.get("url", ""),
        "note": raw_node.get("note", ""),
    }

def repair_next_id():
    for node in world["nodes"]:
        try:
            num = int(str(node["id"])[1:])
            if num >= world["next_id"]:
                world["next_id"] = num + 1
        except Exception:
            pass

def confirm_discard():
    return messagebox.askyesno("Confirm", "Discard current map and start new?")

def atomic_write_json(path, data):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    temp = tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8", dir=parent or None)
    try:
        json.dump(data, temp, indent=2)
        temp.write("\n")
        temp.close()
        shutil.move(temp.name, path)
    except Exception as err:
        try:
            temp.close()
        except Exception:
            pass
        try:
            os.unlink(temp.name)
        except Exception:
            pass
        raise err
