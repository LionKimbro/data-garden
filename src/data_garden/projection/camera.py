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

def value_to_letter(value):
    if 1 <= value <= 26:
        return chr(ord("A") + value - 1)
    return None
