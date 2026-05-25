#!/usr/bin/env python3
# Data Garden - CIRA Phase 1

import json
import math
import os
import shutil
import tempfile
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox

# -----------------------
# CONSTANTS / SYMBOLS
# -----------------------

APP_TITLE = "Data Garden - CIRA Phase 1"
CANVAS_BG = "#111215"
GRID_COLOR = "#22252a"
SELECTION_OUTLINE = "#ffd166"

NODE_KEYS = ("id", "kind", "x", "y", "w", "h", "angle", "fill", "title", "url", "note")

CHORD_BITS = {"a": 16, "s": 8, "d": 4, "f": 2, " ": 1}

COMMAND_NAMES = {
    "CR": "Create Rectangle",
    "CC": "Create Circle",
    "RO": "Rotate Object",
    "MO": "Move Object",
    "CO": "Color Object",
    "DO": "Delete Object",
    "XO": "Clone Object",
    "OL": "Open Link",
    "AA": "Abandon Active",
}

# -----------------------
# GLOBAL BUNDLES
# -----------------------

g = {
    "filepath": None,
    "canvas_hot": False,
}

widgets = {}

raw = {
    "mouse": {},
    "keys": {},
}

continuity = {
    "chord_active": False,
    "chord_keys": set(),
    "chord_timer_id": None,
    "chord_window_ms": 140,
    "pending_letters": [],
    "drag_kind": None,
    "drag_node_id": None,
    "drag_anchor_world": None,
    "drag_start_node": None,
    "pan_last": None,
}

workspace = {
    "selected": None,
    "mode": None,
    "awaiting_click_for": None,
    "camera": {
        "scale": 1.0,
        "ox": 0.0,
        "oy": 0.0,
    },
}

world = {
    "next_id": 1,
    "nodes": [],
}

projection = {
    "items": {},
    "camera": {
        "scale": 1.0,
        "ox": 0.0,
        "oy": 0.0,
    },
}

events = []
effects = []
immediates = []

history = {
    "undo": [],
    "redo": [],
}

# -----------------------
# UI BUILD
# -----------------------

def build_ui():
    root = widgets["root"]
    root.title(APP_TITLE)
    root.geometry("1200x800")
    root.minsize(1000, 600)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    menu = tk.Menu(root)
    widgets["menubar"] = menu
    file_menu = tk.Menu(menu, tearoff=0)
    file_menu.add_command(label="New", command=file_new, accelerator="Ctrl+N")
    file_menu.add_command(label="Open...", command=file_open, accelerator="Ctrl+O")
    file_menu.add_command(label="Save", command=file_save, accelerator="Ctrl+S")
    file_menu.add_command(label="Save As...", command=file_save_as)
    file_menu.add_separator()
    file_menu.add_command(label="Quit", command=root.destroy, accelerator="Ctrl+Q")
    menu.add_cascade(label="File", menu=file_menu)
    root.config(menu=menu)

    paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
    paned.grid(row=0, column=0, sticky="nsew")
    widgets["paned"] = paned

    canvas = tk.Canvas(paned, bg=CANVAS_BG, highlightthickness=0, cursor="arrow")
    widgets["canvas"] = canvas
    paned.add(canvas, weight=3)

    right = ttk.Frame(paned)
    widgets["right"] = right
    right.columnconfigure(1, weight=1)
    paned.add(right, weight=1)

    build_inspector()

    status = ttk.Label(root, text="Ready", anchor="w")
    status.grid(row=1, column=0, sticky="ew")
    widgets["status"] = status

def build_inspector():
    right = widgets["right"]
    widgets["var_id"] = tk.StringVar()
    widgets["var_kind"] = tk.StringVar()
    widgets["var_title"] = tk.StringVar()
    widgets["var_url"] = tk.StringVar()
    widgets["var_fill"] = tk.StringVar(value="#6d4c41")
    widgets["var_w"] = tk.DoubleVar(value=140)
    widgets["var_h"] = tk.DoubleVar(value=100)
    widgets["var_angle"] = tk.DoubleVar(value=0.0)

    row = {"i": 0}

    def lab(text):
        i = row["i"]
        row["i"] += 1
        ttk.Label(right, text=text).grid(row=i, column=0, sticky="w", padx=8, pady=4)
        return i

    def ent(var):
        i = row["i"] - 1
        entry = ttk.Entry(right, textvariable=var, width=36)
        entry.grid(row=i, column=1, sticky="ew", padx=8)
        return entry

    def btn(text, fn):
        i = row["i"]
        row["i"] += 1
        button = ttk.Button(right, text=text, command=fn)
        button.grid(row=i, column=0, columnspan=2, sticky="ew", padx=8, pady=6)
        return button

    lab("Selected ID"); ent(widgets["var_id"])
    lab("Kind"); ent(widgets["var_kind"])
    lab("Title"); ent(widgets["var_title"])
    lab("URL"); ent(widgets["var_url"])
    lab("Fill"); ent(widgets["var_fill"])
    btn("Pick Color", pick_color)
    lab("Width"); ent(widgets["var_w"])
    lab("Height"); ent(widgets["var_h"])
    lab("Angle (deg)"); ent(widgets["var_angle"])

    i = row["i"]
    row["i"] += 1
    ttk.Label(right, text="Note").grid(row=i, column=0, sticky="nw", padx=8, pady=4)
    text = tk.Text(right, height=10, wrap="word")
    text.grid(row=i, column=1, sticky="nsew", padx=8, pady=4)
    widgets["txt_note"] = text
    right.rowconfigure(i, weight=1)

    btn("Apply Changes", apply_inspector)
    btn("Open Link", open_link)
    btn("Delete", delete_selected)
    btn("Clone", clone_selected)

# -----------------------
# UI BINDINGS
# -----------------------

def bind_events():
    root = widgets["root"]
    canvas = widgets["canvas"]

    canvas.bind("<Enter>", on_canvas_enter)
    canvas.bind("<Leave>", on_canvas_leave)
    canvas.bind("<Configure>", on_canvas_configure)

    canvas.bind("<Button-1>", on_left_press)
    canvas.bind("<B1-Motion>", on_left_drag)
    canvas.bind("<ButtonRelease-1>", on_left_release)

    canvas.bind("<Button-2>", on_middle_press)
    canvas.bind("<B2-Motion>", on_middle_drag)
    canvas.bind("<ButtonRelease-2>", on_middle_release)

    canvas.bind("<Button-3>", on_right_press)
    canvas.bind("<B3-Motion>", on_right_drag)
    canvas.bind("<ButtonRelease-3>", on_right_release)

    canvas.bind("<MouseWheel>", on_wheel)
    canvas.bind("<Button-4>", lambda e: on_wheel(e, 120))
    canvas.bind("<Button-5>", lambda e: on_wheel(e, -120))

    root.bind("<KeyPress>", on_keydown)
    root.bind("<KeyRelease>", on_keyup)

    root.bind("<Control-n>", lambda e: file_new())
    root.bind("<Control-o>", lambda e: file_open())
    root.bind("<Control-s>", lambda e: file_save())
    root.bind("<Control-q>", lambda e: root.destroy())

# -----------------------
# CONTINUITY: RAW / CHORDS / MOUSE
# -----------------------

def on_canvas_enter(e):
    g["canvas_hot"] = True

def on_canvas_leave(e):
    g["canvas_hot"] = False

def on_canvas_configure(e):
    refresh_projection()

def on_keydown(e):
    raw["keys"][e.keysym] = True
    if e.keysym == "Escape":
        emit_event({"type": "CANCEL"})
        pump_events()
        refresh_projection()
        return
    chord_keydown(e.keysym)

def on_keyup(e):
    raw["keys"][e.keysym] = False

def chord_keydown(keysym):
    key = keysym.lower()
    if key == "space":
        key = " "
    if key not in CHORD_BITS:
        return
    if not g["canvas_hot"]:
        return

    if not continuity["chord_active"]:
        continuity["chord_active"] = True
        continuity["chord_keys"].clear()
        continuity["chord_timer_id"] = widgets["root"].after(
            continuity["chord_window_ms"],
            chord_finalize,
        )

    continuity["chord_keys"].add(key)

def chord_finalize():
    continuity["chord_active"] = False
    continuity["chord_timer_id"] = None

    value = 0
    for key in continuity["chord_keys"]:
        value += CHORD_BITS[key]
    continuity["chord_keys"].clear()

    letter = value_to_letter(value)
    if letter:
        capture_chord_letter(letter)

def capture_chord_letter(letter):
    status_set("Chord -> " + letter)
    continuity["pending_letters"].append(letter)
    if len(continuity["pending_letters"]) == 2:
        code = "".join(continuity["pending_letters"]).upper()
        continuity["pending_letters"].clear()
        emit_event({"type": "COMMAND_ENTERED", "code": code})
        pump_events()
        refresh_projection()

def on_left_press(e):
    raw["mouse"] = {"x": e.x, "y": e.y, "button": 1}
    wx, wy = screen_to_world(e.x, e.y)

    if workspace["awaiting_click_for"]:
        nid = pick_node(e.x, e.y)
        emit_event({
            "type": "COMMAND_TARGETED",
            "code": workspace["awaiting_click_for"],
            "id": nid,
        })
        pump_events()
        refresh_projection()
        return

    if workspace["mode"] == "create_rect":
        emit_event({"type": "CREATE_NODE", "kind": "rect", "x": wx, "y": wy})
        pump_events()
        refresh_projection()
        return

    if workspace["mode"] == "create_circle":
        emit_event({"type": "CREATE_NODE", "kind": "circle", "x": wx, "y": wy})
        pump_events()
        refresh_projection()
        return

    if workspace["mode"] == "rotate_object" and workspace["selected"]:
        start_drag("rotate", workspace["selected"], wx, wy)
        return

    if workspace["mode"] == "move_object" and workspace["selected"]:
        start_drag("move", workspace["selected"], wx, wy)
        return

    nid = pick_node(e.x, e.y)
    emit_event({"type": "SET_SELECTION", "id": nid})

    pump_events()
    refresh_projection()

def on_left_drag(e):
    raw["mouse"] = {"x": e.x, "y": e.y, "button": 1}
    drag_update(e.x, e.y)

def on_left_release(e):
    stop_drag()

def on_right_press(e):
    raw["mouse"] = {"x": e.x, "y": e.y, "button": 3}
    nid = workspace["selected"]
    if nid:
        wx, wy = screen_to_world(e.x, e.y)
        start_drag("move", nid, wx, wy)

def on_right_drag(e):
    raw["mouse"] = {"x": e.x, "y": e.y, "button": 3}
    drag_update(e.x, e.y)

def on_right_release(e):
    stop_drag()

def on_middle_press(e):
    continuity["pan_last"] = (e.x, e.y)
    widgets["canvas"].config(cursor="fleur")

def on_middle_drag(e):
    if not continuity["pan_last"]:
        return
    lx, ly = continuity["pan_last"]
    dx = e.x - lx
    dy = e.y - ly
    cam = workspace["camera"]
    emit_event({
        "type": "SET_CAMERA",
        "scale": cam["scale"],
        "ox": cam["ox"] + dx,
        "oy": cam["oy"] + dy,
    })
    continuity["pan_last"] = (e.x, e.y)
    pump_events()
    refresh_projection()

def on_middle_release(e):
    continuity["pan_last"] = None
    widgets["canvas"].config(cursor="arrow")

def on_wheel(e, delta=None):
    d = delta
    if d is None:
        d = e.delta

    factor = 1.1
    if d < 0:
        factor = 0.9

    mx, my = e.x, e.y
    wx, wy = screen_to_world(mx, my)
    old_scale = workspace["camera"]["scale"]
    new_scale = max(0.1, min(10.0, old_scale * factor))
    ox = mx - wx * new_scale
    oy = my - wy * new_scale

    emit_event({"type": "SET_CAMERA", "scale": new_scale, "ox": ox, "oy": oy})
    pump_events()
    refresh_projection()

def start_drag(kind, nid, wx, wy):
    continuity["drag_kind"] = kind
    continuity["drag_node_id"] = nid
    continuity["drag_anchor_world"] = (wx, wy)
    continuity["drag_start_node"] = copy_node(find_node(nid))

def drag_update(sx, sy):
    if not continuity["drag_kind"]:
        return
    nid = continuity["drag_node_id"]
    node = find_node(nid)
    if not node:
        stop_drag()
        return

    wx, wy = screen_to_world(sx, sy)

    if continuity["drag_kind"] == "move":
        ax, ay = continuity["drag_anchor_world"]
        dx = wx - ax
        dy = wy - ay
        # TODO Phase 2: collapse drag frames into one undoable MOVE_NODE on release.
        emit_event({"type": "MOVE_NODE", "id": nid, "x": node["x"] + dx, "y": node["y"] + dy})
        continuity["drag_anchor_world"] = (wx, wy)

    if continuity["drag_kind"] == "rotate":
        angle = math.degrees(math.atan2(wy - node["y"], wx - node["x"]))
        # TODO Phase 2: collapse drag frames into one undoable ROTATE_NODE on release.
        emit_event({"type": "ROTATE_NODE", "id": nid, "angle": angle})

    pump_events()
    refresh_projection()

def stop_drag():
    continuity["drag_kind"] = None
    continuity["drag_node_id"] = None
    continuity["drag_anchor_world"] = None
    continuity["drag_start_node"] = None

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

# -----------------------
# DISCRETE: EVENTS
# -----------------------

def emit_event(event):
    events.append(event)

# -----------------------
# DISCRETE: REDUCER
# -----------------------

def reduce_event(event):
    kind = event["type"]

    if kind == "COMMAND_ENTERED":
        reduce_command(event["code"])
        return

    if kind == "COMMAND_TARGETED":
        reduce_command_targeted(event)
        return

    if kind == "CANCEL":
        workspace["mode"] = None
        workspace["awaiting_click_for"] = None
        continuity["pending_letters"].clear()
        effects.append({"type": "STATUS", "text": "Ready"})
        return

    if kind == "SET_MODE":
        workspace["mode"] = event["mode"]
        effects.append({"type": "STATUS", "text": "Mode: " + str(event["mode"])})
        return

    if kind == "SET_SELECTION":
        workspace["selected"] = event["id"]
        effects.append({"type": "INSPECTOR_REFRESH"})
        return

    if kind == "CREATE_NODE":
        workspace["mode"] = None
        effects.append({
            "type": "WORLD_CREATE_NODE",
            "kind": event["kind"],
            "x": event["x"],
            "y": event["y"],
        })
        return

    if kind == "DELETE_NODE":
        effects.append({"type": "WORLD_DELETE_NODE", "id": event["id"]})
        return

    if kind == "CLONE_NODE":
        effects.append({"type": "WORLD_CLONE_NODE", "id": event["id"]})
        return

    if kind == "SET_NODE_FILL":
        effects.append({"type": "WORLD_UPDATE_NODE", "id": event["id"], "fields": {"fill": event["fill"]}})
        return

    if kind == "UPDATE_NODE":
        effects.append({"type": "WORLD_UPDATE_NODE", "id": event["id"], "fields": event["fields"]})
        return

    if kind == "MOVE_NODE":
        effects.append({"type": "WORLD_UPDATE_NODE", "id": event["id"], "fields": {"x": event["x"], "y": event["y"]}})
        return

    if kind == "ROTATE_NODE":
        effects.append({"type": "WORLD_UPDATE_NODE", "id": event["id"], "fields": {"angle": event["angle"]}})
        return

    if kind == "SET_CAMERA":
        workspace["camera"]["scale"] = event["scale"]
        workspace["camera"]["ox"] = event["ox"]
        workspace["camera"]["oy"] = event["oy"]
        return

    if kind == "OPEN_LINK":
        effects.append({"type": "OPEN_LINK", "id": event["id"]})
        return

    if kind == "NEW_PROJECT":
        workspace["selected"] = None
        workspace["mode"] = None
        workspace["awaiting_click_for"] = None
        reset_camera()
        effects.append({"type": "WORLD_NEW"})
        effects.append({"type": "INSPECTOR_REFRESH"})
        effects.append({"type": "STATUS", "text": "New project"})
        return

    if kind == "LOAD_PROJECT":
        workspace["selected"] = None
        workspace["mode"] = None
        workspace["awaiting_click_for"] = None
        load_camera(event["data"])
        effects.append({"type": "WORLD_LOAD", "data": event["data"]})
        effects.append({"type": "INSPECTOR_REFRESH"})
        return

    effects.append({"type": "STATUS", "text": "Unhandled event: " + kind})

def reduce_command(code):
    name = COMMAND_NAMES.get(code)
    if not name:
        workspace["mode"] = None
        effects.append({"type": "STATUS", "text": "Unknown command: " + code})
        return

    effects.append({"type": "STATUS", "text": code + ": " + name})

    if code == "CR":
        workspace["mode"] = "create_rect"
        return
    if code == "CC":
        workspace["mode"] = "create_circle"
        return
    if code == "RO":
        workspace["mode"] = "rotate_object"
        return
    if code == "MO":
        workspace["mode"] = "move_object"
        return
    if code == "AA":
        workspace["selected"] = None
        workspace["mode"] = None
        workspace["awaiting_click_for"] = None
        effects.append({"type": "INSPECTOR_REFRESH"})
        return

    reduce_object_command(code, workspace["selected"])

def reduce_command_targeted(event):
    code = event["code"]
    workspace["awaiting_click_for"] = None
    if not event["id"]:
        effects.append({"type": "STATUS", "text": code + " cancelled"})
        return
    workspace["selected"] = event["id"]
    effects.append({"type": "INSPECTOR_REFRESH"})
    reduce_object_command(code, event["id"])

def reduce_object_command(code, nid):
    if code == "CO":
        if nid:
            effects.append({"type": "ASK_COLOR", "id": nid})
        else:
            workspace["awaiting_click_for"] = "CO"
            effects.append({"type": "STATUS", "text": "CO: click a node to color it, or click empty space to cancel"})
        return

    if code == "DO":
        if nid:
            effects.append({"type": "ASK_DELETE", "id": nid})
        else:
            workspace["awaiting_click_for"] = "DO"
            effects.append({"type": "STATUS", "text": "DO: click a node to delete it, or click empty space to cancel"})
        return

    if code == "XO":
        if nid:
            effects.append({"type": "WORLD_CLONE_NODE", "id": nid})
        else:
            workspace["awaiting_click_for"] = "XO"
            effects.append({"type": "STATUS", "text": "XO: click a node to clone it, or click empty space to cancel"})
        return

    if code == "OL":
        if nid:
            effects.append({"type": "OPEN_LINK", "id": nid})
        else:
            workspace["awaiting_click_for"] = "OL"
            effects.append({"type": "STATUS", "text": "OL: click a node to open its link, or click empty space to cancel"})
        return

# -----------------------
# EFFECT ROUTING
# -----------------------

def route_effect(effect):
    kind = effect["type"]

    if kind == "STATUS":
        status_set(effect["text"])
        return

    if kind == "INSPECTOR_REFRESH":
        refresh_inspector()
        return

    if kind == "WORLD_CREATE_NODE":
        node = create_node(effect["kind"], effect["x"], effect["y"])
        emit_event({"type": "SET_SELECTION", "id": node["id"]})
        effects.append({"type": "STATUS", "text": "Created " + node["kind"] + " " + node["id"]})
        return

    if kind == "WORLD_DELETE_NODE":
        delete_node(effect["id"])
        emit_event({"type": "SET_SELECTION", "id": None})
        effects.append({"type": "STATUS", "text": "Object deleted"})
        return

    if kind == "WORLD_CLONE_NODE":
        node = clone_node(effect["id"])
        if node:
            emit_event({"type": "SET_SELECTION", "id": node["id"]})
            effects.append({"type": "STATUS", "text": "Object cloned"})
        return

    if kind == "WORLD_UPDATE_NODE":
        update_node(effect["id"], effect["fields"])
        effects.append({"type": "INSPECTOR_REFRESH"})
        return

    if kind == "WORLD_NEW":
        reset_world()
        g["filepath"] = None
        return

    if kind == "WORLD_LOAD":
        load_world(effect["data"])
        return

    if kind == "ASK_COLOR":
        ask_color(effect["id"])
        return

    if kind == "ASK_DELETE":
        ask_delete(effect["id"])
        return

    if kind == "OPEN_LINK":
        open_node_link(effect["id"])
        return

def ask_color(nid):
    node = find_node(nid)
    if not node:
        return
    choice = colorchooser.askcolor(color=node["fill"], title="Pick Fill Color")
    if choice and choice[1]:
        emit_event({"type": "SET_NODE_FILL", "id": nid, "fill": choice[1]})
        pump_events()
        refresh_projection()

def ask_delete(nid):
    if messagebox.askyesno("Delete", "Delete selected object?"):
        emit_event({"type": "DELETE_NODE", "id": nid})
        pump_events()
        refresh_projection()
    else:
        status_set("Object deletion cancelled")

def open_node_link(nid):
    node = find_node(nid)
    if not node:
        return
    if node["url"]:
        webbrowser.open(node["url"])
        status_set("Opened link")
    else:
        messagebox.showinfo("No URL", "Selected node has no URL set.")

# -----------------------
# WORLD MODEL
# -----------------------

def create_node(kind, x, y):
    fill = "#6d4c41"
    w = 140
    h = 100
    if kind == "circle":
        fill = "#3a6ea5"
        w = 120
        h = 120

    node = {
        "id": gen_id(),
        "kind": kind,
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "angle": 0.0,
        "fill": fill,
        "title": "",
        "url": "",
        "note": "",
    }
    world["nodes"].append(node)
    return node

def clone_node(nid):
    source = find_node(nid)
    if not source:
        return None
    node = copy_node(source)
    node["id"] = gen_id()
    node["x"] += 40
    node["y"] += 40
    node["title"] = node["title"] + " (copy)"
    world["nodes"].append(node)
    return node

def delete_node(nid):
    world["nodes"][:] = [node for node in world["nodes"] if node["id"] != nid]

def update_node(nid, fields):
    node = find_node(nid)
    if not node:
        return
    for key in fields:
        if key in NODE_KEYS and key != "id":
            node[key] = fields[key]

def find_node(nid):
    for node in world["nodes"]:
        if node["id"] == nid:
            return node
    return None

def copy_node(node):
    copied = {}
    for key in NODE_KEYS:
        copied[key] = node[key]
    return copied

def gen_id():
    nid = "n" + str(world["next_id"])
    world["next_id"] += 1
    return nid

def reset_world():
    world["nodes"].clear()
    world["next_id"] = 1

def reset_camera():
    workspace["camera"]["scale"] = 1.0
    workspace["camera"]["ox"] = 0.0
    workspace["camera"]["oy"] = 0.0

# -----------------------
# PROJECTION
# -----------------------

def refresh_projection():
    realize_camera()
    draw_grid()
    draw_nodes()
    draw_selection()

def realize_camera():
    projection["camera"]["scale"] = workspace["camera"]["scale"]
    projection["camera"]["ox"] = workspace["camera"]["ox"]
    projection["camera"]["oy"] = workspace["camera"]["oy"]

def draw_grid():
    canvas = widgets["canvas"]
    canvas.delete("grid")

    width = canvas.winfo_width() or 1200
    height = canvas.winfo_height() or 800
    step = 100

    wx0, wy0 = screen_to_world(0, 0)
    wx1, wy1 = screen_to_world(width, height)

    gx0 = int(math.floor(wx0 / step) * step)
    gy0 = int(math.floor(wy0 / step) * step)
    gx1 = int(math.ceil(wx1 / step) * step)
    gy1 = int(math.ceil(wy1 / step) * step)

    for x in range(gx0, gx1 + 1, step):
        x0, y0 = world_to_screen(x, gy0)
        x1, y1 = world_to_screen(x, gy1)
        canvas.create_line(x0, y0, x1, y1, fill=GRID_COLOR, tags=("grid",))

    for y in range(gy0, gy1 + 1, step):
        x0, y0 = world_to_screen(gx0, y)
        x1, y1 = world_to_screen(gx1, y)
        canvas.create_line(x0, y0, x1, y1, fill=GRID_COLOR, tags=("grid",))

    canvas.tag_lower("grid")

def draw_nodes():
    canvas = widgets["canvas"]
    canvas.delete("node")
    projection["items"].clear()

    for node in world["nodes"]:
        item = draw_node(node)
        if item:
            projection["items"][item] = node["id"]

def draw_node(node):
    if node["kind"] == "rect":
        return draw_rect_node(node)
    if node["kind"] == "circle":
        return draw_circle_node(node)
    return None

def draw_rect_node(node):
    canvas = widgets["canvas"]
    points = rect_points(node)
    return canvas.create_polygon(
        points,
        fill=node["fill"],
        outline="",
        tags=("node", "n:" + node["id"]),
    )

def draw_circle_node(node):
    canvas = widgets["canvas"]
    cx, cy = world_to_screen(node["x"], node["y"])
    scale = projection["camera"]["scale"]
    rx = node["w"] * scale / 2
    ry = node["h"] * scale / 2
    return canvas.create_oval(
        cx - rx,
        cy - ry,
        cx + rx,
        cy + ry,
        fill=node["fill"],
        outline="",
        tags=("node", "n:" + node["id"]),
    )

def draw_selection():
    canvas = widgets["canvas"]
    canvas.delete("sel")
    nid = workspace["selected"]
    if not nid:
        return
    node = find_node(nid)
    if not node:
        return

    if node["kind"] == "rect":
        canvas.create_polygon(
            rect_points(node),
            fill="",
            outline=SELECTION_OUTLINE,
            width=2,
            tags=("sel",),
        )
        return

    if node["kind"] == "circle":
        cx, cy = world_to_screen(node["x"], node["y"])
        scale = projection["camera"]["scale"]
        rx = node["w"] * scale / 2
        ry = node["h"] * scale / 2
        canvas.create_oval(
            cx - rx,
            cy - ry,
            cx + rx,
            cy + ry,
            fill="",
            outline=SELECTION_OUTLINE,
            width=2,
            tags=("sel",),
        )

def rect_points(node):
    cx, cy = world_to_screen(node["x"], node["y"])
    scale = projection["camera"]["scale"]
    width = node["w"] * scale
    height = node["h"] * scale
    angle = math.radians(node["angle"])
    dx = width / 2
    dy = height / 2
    corners = [(-dx, -dy), (dx, -dy), (dx, dy), (-dx, dy)]
    points = []
    cs = math.cos(angle)
    sn = math.sin(angle)
    for x, y in corners:
        rx = x * cs - y * sn
        ry = x * sn + y * cs
        points.extend([cx + rx, cy + ry])
    return points

# -----------------------
# INSPECTOR
# -----------------------

def refresh_inspector():
    nid = workspace["selected"]
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
    nid = workspace["selected"]
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
    nid = workspace["selected"]
    if not nid:
        return
    emit_event({"type": "COMMAND_ENTERED", "code": "CO"})
    pump_events()
    refresh_projection()

def open_link():
    nid = workspace["selected"]
    if not nid:
        return
    emit_event({"type": "OPEN_LINK", "id": nid})
    pump_events()

def delete_selected():
    nid = workspace["selected"]
    if not nid:
        return
    emit_event({"type": "COMMAND_ENTERED", "code": "DO"})
    pump_events()
    refresh_projection()

def clone_selected():
    nid = workspace["selected"]
    if not nid:
        return
    emit_event({"type": "COMMAND_ENTERED", "code": "XO"})
    pump_events()
    refresh_projection()

def status_set(text):
    widgets["status"].config(text=text)

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
    try:
        data = read_json(path)
    except Exception as err:
        messagebox.showerror("Open failed", str(err))
        return
    emit_event({"type": "LOAD_PROJECT", "data": data})
    pump_events()
    g["filepath"] = path
    status_set("Opened " + os.path.basename(path))
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
    else:
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

# -----------------------
# HISTORY PLACEHOLDER
# -----------------------

def clear_history():
    history["undo"].clear()
    history["redo"].clear()

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

if __name__ == "__main__":
    main()
