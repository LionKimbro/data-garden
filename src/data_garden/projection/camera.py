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
# CONTINUITY: PICKING / COORDINATES
# -----------------------

def world_to_screen(x, y):
    cam = projection["camera"]
    return (x * cam["scale"] + cam["ox"], y * cam["scale"] + cam["oy"])

def screen_to_world(sx, sy):
    cam = projection["camera"]
    return ((sx - cam["ox"]) / cam["scale"], (sy - cam["oy"]) / cam["scale"])

def pick_node(sx, sy):
    canvas = widgets["canvas"]
    items = canvas.find_overlapping(sx - 1, sy - 1, sx + 1, sy + 1)
    for item in reversed(items):
        if "node" in canvas.gettags(item):
            return item_to_node_id(item)
    return None

def item_to_node_id(item):
    canvas = widgets["canvas"]
    tags = canvas.gettags(item)
    for tag in tags:
        if tag.startswith("n:"):
            return tag[2:]
    return None

def frame_points_screen(bounds):
    x0, y0, x1, y1 = bounds
    sx0, sy0 = world_to_screen(x0, y0)
    sx1, sy1 = world_to_screen(x1, y1)
    return {
        "nw": (sx0, sy0),
        "ne": (sx1, sy0),
        "se": (sx1, sy1),
        "sw": (sx0, sy1),
        "n": ((sx0 + sx1) / 2, sy0),
    }

def handle_specs_for_selection():
    if not workspace["manipulation"]["visible"]:
        return []
    if not selection_ids():
        return []
    bounds = selected_bounds_world()
    if not bounds:
        return []
    points = frame_points_screen(bounds)
    if workspace["manipulation"]["kind"] == "rotate":
        x, y = points["n"]
        return [{
            "kind": "handle",
            "handle_kind": "rotate",
            "handle_name": "rotate",
            "manipulation_kind": workspace["manipulation"]["kind"],
            "shape": "circle",
            "sx": x,
            "sy": y - 28,
            "radius": 6,
        }]
    specs = []
    for name in ("nw", "ne", "sw", "se"):
        x, y = points[name]
        specs.append({
            "kind": "handle",
            "handle_kind": "size",
            "handle_name": name,
            "manipulation_kind": workspace["manipulation"]["kind"],
            "shape": "square",
            "sx": x,
            "sy": y,
            "radius": 5,
        })
    return specs

def handle_hit_test(sx, sy):
    for spec in reversed(handle_specs_for_selection()):
        radius = spec["radius"] + 3
        if abs(sx - spec["sx"]) <= radius and abs(sy - spec["sy"]) <= radius:
            return {
                "kind": "handle",
                "node_id": None,
                "handle_kind": spec["handle_kind"],
                "handle_name": spec["handle_name"],
                "manipulation_kind": spec["manipulation_kind"],
            }
    return None

def value_to_letter(value):
    if 1 <= value <= 26:
        return chr(ord("A") + value - 1)
    return None
