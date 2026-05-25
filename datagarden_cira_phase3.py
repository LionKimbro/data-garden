#!/usr/bin/env python3
# Data Garden - CIRA Phase 3

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

APP_TITLE = "Data Garden - CIRA Phase 3"
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
    "UU": "Undo",
    "RR": "Redo",
}

# -----------------------
# GLOBAL BUNDLES
# -----------------------

g = {
    "filepath": None,
    "canvas_hot": False,
    "restoring_history": False,
}

widgets = {}

raw = {
    "current": {
        "sx": 0,
        "sy": 0,
        "inside_canvas": False,
        "button_1_down": False,
        "button_2_down": False,
        "button_3_down": False,
        "keys_down": set(),
        "last_event_kind": None,
        "last_key": None,
        "wheel_delta": 0,
        "time_ms": 0,
    },
    "previous": {
        "sx": 0,
        "sy": 0,
        "inside_canvas": False,
        "button_1_down": False,
        "button_2_down": False,
        "button_3_down": False,
        "keys_down": set(),
        "last_event_kind": None,
        "last_key": None,
        "wheel_delta": 0,
        "time_ms": 0,
    },
}

derived = {}

tokenizer_state = {
    "drag_anchor_sx": 0,
    "drag_anchor_sy": 0,
}

judge = {
    "owners": {},
}

organisms = {
    "chord": {
        "state": "idle",
        "keys": set(),
        "timer_id": None,
        "window_ms": 140,
        "pending_letters": [],
    },
    "move": {
        "state": "idle",
        "pointer": None,
        "node_id": None,
        "anchor_world": None,
        "start_checkpoint": None,
        "changed": False,
    },
    "rotate": {
        "state": "idle",
        "pointer": None,
        "node_id": None,
        "start_checkpoint": None,
        "changed": False,
    },
    "camera_pan": {
        "state": "idle",
        "last": None,
    },
    "camera": {
        "start_checkpoint": None,
        "changed": False,
        "timer_id": None,
        "window_ms": 350,
    },
}

continuity = {
    "cycle": 0,
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
    "limit": 100,
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
    root.bind("<Control-z>", lambda e: undo_history())
    root.bind("<Control-y>", lambda e: redo_history())
    root.bind("<Control-q>", lambda e: root.destroy())

# -----------------------
# CONTINUITY: RAW / TOKENIZERS / ORGANISMS
# -----------------------

def on_canvas_enter(e):
    raw_update_pointer(e)
    raw["current"]["inside_canvas"] = True
    g["canvas_hot"] = True
    raw["current"]["last_event_kind"] = "enter"
    run_app_cycle()

def on_canvas_leave(e):
    raw_update_pointer(e)
    raw["current"]["inside_canvas"] = False
    g["canvas_hot"] = False
    raw["current"]["last_event_kind"] = "leave"
    run_app_cycle()

def on_canvas_configure(e):
    refresh_projection()

def on_keydown(e):
    raw_set_key(e.keysym, True)
    raw["current"]["last_event_kind"] = "key_press"
    raw["current"]["last_key"] = e.keysym
    run_app_cycle()

def on_keyup(e):
    raw_set_key(e.keysym, False)
    raw["current"]["last_event_kind"] = "key_release"
    raw["current"]["last_key"] = e.keysym
    run_app_cycle()

def on_left_press(e):
    raw_update_pointer(e)
    raw_set_button(1, True)
    raw["current"]["last_event_kind"] = "button_press"
    run_app_cycle()

def on_left_drag(e):
    raw_update_pointer(e)
    raw["current"]["last_event_kind"] = "motion"
    run_app_cycle()

def on_left_release(e):
    raw_update_pointer(e)
    raw_set_button(1, False)
    raw["current"]["last_event_kind"] = "button_release"
    run_app_cycle()

def on_right_press(e):
    raw_update_pointer(e)
    raw_set_button(3, True)
    raw["current"]["last_event_kind"] = "button_press"
    run_app_cycle()

def on_right_drag(e):
    raw_update_pointer(e)
    raw["current"]["last_event_kind"] = "motion"
    run_app_cycle()

def on_right_release(e):
    raw_update_pointer(e)
    raw_set_button(3, False)
    raw["current"]["last_event_kind"] = "button_release"
    run_app_cycle()

def on_middle_press(e):
    raw_update_pointer(e)
    raw_set_button(2, True)
    raw["current"]["last_event_kind"] = "button_press"
    run_app_cycle()

def on_middle_drag(e):
    raw_update_pointer(e)
    raw["current"]["last_event_kind"] = "motion"
    run_app_cycle()

def on_middle_release(e):
    raw_update_pointer(e)
    raw_set_button(2, False)
    raw["current"]["last_event_kind"] = "button_release"
    run_app_cycle()

def on_wheel(e, delta=None):
    raw_update_pointer(e)
    if delta is None:
        delta = e.delta
    raw["current"]["wheel_delta"] = delta
    raw["current"]["last_event_kind"] = "wheel"
    run_app_cycle()

def raw_update_pointer(e):
    raw["current"]["sx"] = e.x
    raw["current"]["sy"] = e.y
    raw["current"]["time_ms"] = getattr(e, "time", raw["current"]["time_ms"])

def raw_set_button(button, is_down):
    raw["current"]["button_" + str(button) + "_down"] = is_down

def raw_set_key(keysym, is_down):
    if is_down:
        raw["current"]["keys_down"].add(keysym)
    else:
        raw["current"]["keys_down"].discard(keysym)

def run_app_cycle():
    run_continuity_cycle()
    pump_events()
    refresh_projection()
    clear_immediates()
    finish_raw_cycle()

def run_continuity_cycle():
    derived.clear()
    run_tokenizers()
    run_organisms()

def finish_raw_cycle():
    raw["previous"].clear()
    for key in raw["current"]:
        value = raw["current"][key]
        if key == "keys_down":
            raw["previous"][key] = set(value)
        else:
            raw["previous"][key] = value
    raw["current"]["last_event_kind"] = None
    raw["current"]["last_key"] = None
    raw["current"]["wheel_delta"] = 0

def clear_immediates():
    immediates.clear()

def judge_clear():
    judge["owners"].clear()

def judge_check(owner, resources):
    for resource in resources:
        current_owner = judge_owner(resource)
        if current_owner and current_owner != owner:
            return False
    return True

def judge_commit(owner, resources):
    if not judge_check(owner, resources):
        return False
    for resource in resources:
        judge["owners"][resource] = owner
    return True

def judge_release(owner):
    remove = []
    for resource in judge["owners"]:
        if judge["owners"][resource] == owner:
            remove.append(resource)
    for resource in remove:
        del judge["owners"][resource]

def judge_owner(resource):
    return judge["owners"].get(resource)

def cancel_timer(name):
    root = widgets.get("root")
    timer_id = organisms[name]["timer_id"]
    if root and timer_id:
        try:
            root.after_cancel(timer_id)
        except Exception:
            pass
    organisms[name]["timer_id"] = None

def reset_chord_organism():
    cancel_timer("chord")
    organisms["chord"]["state"] = "idle"
    organisms["chord"]["keys"].clear()
    organisms["chord"]["pending_letters"].clear()
    judge_release("chord")

def reset_move_organism():
    organisms["move"]["state"] = "idle"
    organisms["move"]["pointer"] = None
    organisms["move"]["node_id"] = None
    organisms["move"]["anchor_world"] = None
    organisms["move"]["start_checkpoint"] = None
    organisms["move"]["changed"] = False

def reset_rotate_organism():
    organisms["rotate"]["state"] = "idle"
    organisms["rotate"]["pointer"] = None
    organisms["rotate"]["node_id"] = None
    organisms["rotate"]["start_checkpoint"] = None
    organisms["rotate"]["changed"] = False

def reset_camera_organisms():
    cancel_timer("camera")
    organisms["camera"]["start_checkpoint"] = None
    organisms["camera"]["changed"] = False
    organisms["camera_pan"]["state"] = "idle"
    organisms["camera_pan"]["last"] = None
    if "canvas" in widgets:
        widgets["canvas"].config(cursor="arrow")
    judge_release("camera_pan")

def run_tokenizers():
    tokenize_pointer()
    tokenize_buttons()
    tokenize_keyboard()
    tokenize_target()
    tokenize_drag()
    tokenize_wheel()

def tokenize_pointer():
    sx = raw["current"]["sx"]
    sy = raw["current"]["sy"]
    psx = raw["previous"]["sx"]
    psy = raw["previous"]["sy"]
    wx, wy = screen_to_world(sx, sy)
    derived["pointer"] = {
        "sx": sx,
        "sy": sy,
        "wx": wx,
        "wy": wy,
        "dx": sx - psx,
        "dy": sy - psy,
        "moving": sx != psx or sy != psy,
        "inside_canvas": raw["current"]["inside_canvas"],
    }

def tokenize_buttons():
    current = raw["current"]
    previous = raw["previous"]
    derived["buttons"] = {
        "b1_pressed": current["button_1_down"] and not previous["button_1_down"],
        "b1_released": not current["button_1_down"] and previous["button_1_down"],
        "b1_down": current["button_1_down"],
        "b2_pressed": current["button_2_down"] and not previous["button_2_down"],
        "b2_released": not current["button_2_down"] and previous["button_2_down"],
        "b2_down": current["button_2_down"],
        "b3_pressed": current["button_3_down"] and not previous["button_3_down"],
        "b3_released": not current["button_3_down"] and previous["button_3_down"],
        "b3_down": current["button_3_down"],
    }

def tokenize_keyboard():
    current = raw["current"]
    previous = raw["previous"]
    derived["keyboard"] = {
        "key_pressed": current["last_key"] if current["last_event_kind"] == "key_press" else None,
        "key_released": current["last_key"] if current["last_event_kind"] == "key_release" else None,
        "keys_down": set(current["keys_down"]),
        "changed": current["keys_down"] != previous["keys_down"],
    }

def tokenize_target():
    nid = None
    if raw["current"]["inside_canvas"] and "canvas" in widgets:
        nid = pick_node(raw["current"]["sx"], raw["current"]["sy"])
    derived["target"] = {
        "node_id": nid,
        "kind": "node" if nid else None,
    }

def tokenize_drag():
    buttons = derived["buttons"]
    pointer = derived["pointer"]
    if buttons["b1_pressed"] or buttons["b2_pressed"] or buttons["b3_pressed"]:
        tokenizer_state["drag_anchor_sx"] = pointer["sx"]
        tokenizer_state["drag_anchor_sy"] = pointer["sy"]
    dx = pointer["sx"] - tokenizer_state["drag_anchor_sx"]
    dy = pointer["sy"] - tokenizer_state["drag_anchor_sy"]
    derived["drag"] = {
        "threshold_crossed": abs(dx) >= 2 or abs(dy) >= 2,
    }

def tokenize_wheel():
    derived["wheel"] = {
        "delta": raw["current"]["wheel_delta"],
    }

def run_organisms():
    run_chord_organism()
    run_awaiting_target_organism()
    run_create_object_organism()
    run_camera_pan_organism()
    run_camera_zoom_organism()
    run_rotate_object_organism()
    run_move_object_organism()
    run_click_selection_organism()

def run_chord_organism():
    key = derived["keyboard"]["key_pressed"]
    if key == "Escape":
        emit_event({"type": "CANCEL"})
        reset_chord_organism()
        return
    key = normalize_chord_key(key)
    if not key:
        return
    if not raw["current"]["inside_canvas"]:
        return
    if not judge_commit("chord", ["keyboard:chord"]):
        return
    chord = organisms["chord"]
    if chord["state"] == "idle":
        chord["state"] = "collecting"
        chord["keys"].clear()
        chord["timer_id"] = widgets["root"].after(chord["window_ms"], finalize_chord_organism)
    chord["keys"].add(key)

def normalize_chord_key(keysym):
    if not keysym:
        return None
    key = keysym.lower()
    if key == "space":
        key = " "
    if key in CHORD_BITS:
        return key
    return None

def finalize_chord_organism():
    chord = organisms["chord"]
    chord["timer_id"] = None
    chord["state"] = "idle"
    value = 0
    for key in chord["keys"]:
        value += CHORD_BITS[key]
    chord["keys"].clear()
    judge_release("chord")
    letter = value_to_letter(value)
    if letter:
        capture_chord_letter(letter)
        pump_events()
        refresh_projection()
        clear_immediates()

def capture_chord_letter(letter):
    status_set("Chord -> " + letter)
    chord = organisms["chord"]
    chord["pending_letters"].append(letter)
    if len(chord["pending_letters"]) == 2:
        code = "".join(chord["pending_letters"]).upper()
        chord["pending_letters"].clear()
        emit_event({"type": "COMMAND_ENTERED", "code": code})

def run_awaiting_target_organism():
    if not workspace["awaiting_click_for"]:
        return
    if not derived["buttons"]["b1_pressed"]:
        return
    if not judge_commit("awaiting_target", ["pointer:left", "selection"]):
        return
    emit_event({
        "type": "COMMAND_TARGETED",
        "code": workspace["awaiting_click_for"],
        "id": derived["target"]["node_id"],
    })
    judge_release("awaiting_target")

def run_create_object_organism():
    if workspace["mode"] not in ("create_rect", "create_circle"):
        return
    if not derived["buttons"]["b1_pressed"]:
        return
    if not judge_commit("create_object", ["pointer:left"]):
        return
    kind = "rect"
    if workspace["mode"] == "create_circle":
        kind = "circle"
    emit_event({
        "type": "CREATE_NODE",
        "kind": kind,
        "x": derived["pointer"]["wx"],
        "y": derived["pointer"]["wy"],
    })
    judge_release("create_object")

def run_click_selection_organism():
    if not derived["buttons"]["b1_pressed"]:
        return
    if workspace["awaiting_click_for"]:
        return
    if workspace["mode"] in ("create_rect", "create_circle", "move_object", "rotate_object"):
        return
    if not judge_commit("click_selection", ["pointer:left", "selection"]):
        return
    emit_event({"type": "SET_SELECTION", "id": derived["target"]["node_id"]})
    judge_release("click_selection")

def run_move_object_organism():
    move = organisms["move"]
    if move["state"] == "idle":
        start_move_organism()
        return
    if move["state"] == "active":
        update_move_organism()

def start_move_organism():
    selected = workspace["selected"]
    if not selected:
        return
    pointer_name = None
    if derived["buttons"]["b3_pressed"]:
        pointer_name = "right"
    if derived["buttons"]["b1_pressed"] and workspace["mode"] == "move_object":
        pointer_name = "left"
    if not pointer_name:
        return
    resources = ["pointer:" + pointer_name, "selection", "node:" + selected]
    if not judge_commit("move_object", resources):
        return
    move = organisms["move"]
    move["state"] = "active"
    move["pointer"] = pointer_name
    move["node_id"] = selected
    move["anchor_world"] = (derived["pointer"]["wx"], derived["pointer"]["wy"])
    move["start_checkpoint"] = snapshot_state()
    move["changed"] = False

def update_move_organism():
    move = organisms["move"]
    node = find_node(move["node_id"])
    if not node:
        stop_move_organism()
        return
    buttons = derived["buttons"]
    if (move["pointer"] == "left" and buttons["b1_released"]) or (move["pointer"] == "right" and buttons["b3_released"]):
        stop_move_organism()
        return
    if not derived["pointer"]["moving"]:
        return
    ax, ay = move["anchor_world"]
    wx = derived["pointer"]["wx"]
    wy = derived["pointer"]["wy"]
    emit_event({"type": "PREVIEW_NODE", "id": node["id"], "fields": {"x": node["x"] + wx - ax, "y": node["y"] + wy - ay}})
    move["anchor_world"] = (wx, wy)
    move["changed"] = True

def stop_move_organism():
    move = organisms["move"]
    if move["changed"]:
        emit_event({"type": "COMMIT_DRAG", "checkpoint": move["start_checkpoint"]})
    reset_move_organism()
    judge_release("move_object")

def run_rotate_object_organism():
    rotate = organisms["rotate"]
    if rotate["state"] == "idle":
        start_rotate_organism()
        return
    if rotate["state"] == "active":
        update_rotate_organism()

def start_rotate_organism():
    selected = workspace["selected"]
    if not selected:
        return
    if workspace["mode"] != "rotate_object":
        return
    if not derived["buttons"]["b1_pressed"]:
        return
    if not judge_commit("rotate_object", ["pointer:left", "selection", "node:" + selected]):
        return
    rotate = organisms["rotate"]
    rotate["state"] = "active"
    rotate["pointer"] = "left"
    rotate["node_id"] = selected
    rotate["start_checkpoint"] = snapshot_state()
    rotate["changed"] = False

def update_rotate_organism():
    rotate = organisms["rotate"]
    node = find_node(rotate["node_id"])
    if not node:
        stop_rotate_organism()
        return
    if derived["buttons"]["b1_released"]:
        stop_rotate_organism()
        return
    if not derived["pointer"]["moving"]:
        return
    angle = math.degrees(math.atan2(derived["pointer"]["wy"] - node["y"], derived["pointer"]["wx"] - node["x"]))
    emit_event({"type": "PREVIEW_NODE", "id": node["id"], "fields": {"angle": angle}})
    rotate["changed"] = True

def stop_rotate_organism():
    rotate = organisms["rotate"]
    if rotate["changed"]:
        emit_event({"type": "COMMIT_DRAG", "checkpoint": rotate["start_checkpoint"]})
    reset_rotate_organism()
    judge_release("rotate_object")

def run_camera_pan_organism():
    pan = organisms["camera_pan"]
    if pan["state"] == "idle":
        if not derived["buttons"]["b2_pressed"]:
            return
        if not judge_commit("camera_pan", ["pointer:middle", "camera"]):
            return
        begin_camera_episode()
        pan["state"] = "active"
        pan["last"] = (derived["pointer"]["sx"], derived["pointer"]["sy"])
        widgets["canvas"].config(cursor="fleur")
        return
    if pan["state"] == "active":
        if derived["buttons"]["b2_released"]:
            schedule_camera_commit()
            pan["state"] = "idle"
            pan["last"] = None
            widgets["canvas"].config(cursor="arrow")
            judge_release("camera_pan")
            return
        if not derived["pointer"]["moving"]:
            return
        lx, ly = pan["last"]
        sx = derived["pointer"]["sx"]
        sy = derived["pointer"]["sy"]
        cam = workspace["camera"]
        emit_event({"type": "SET_CAMERA", "scale": cam["scale"], "ox": cam["ox"] + sx - lx, "oy": cam["oy"] + sy - ly})
        pan["last"] = (sx, sy)
        organisms["camera"]["changed"] = True

def run_camera_zoom_organism():
    delta = derived["wheel"]["delta"]
    if not delta:
        return
    if not judge_check("camera_zoom", ["camera"]):
        return
    begin_camera_episode()
    factor = 1.1
    if delta < 0:
        factor = 0.9
    sx = derived["pointer"]["sx"]
    sy = derived["pointer"]["sy"]
    wx = derived["pointer"]["wx"]
    wy = derived["pointer"]["wy"]
    old_scale = workspace["camera"]["scale"]
    new_scale = max(0.1, min(10.0, old_scale * factor))
    emit_event({"type": "SET_CAMERA", "scale": new_scale, "ox": sx - wx * new_scale, "oy": sy - wy * new_scale})
    organisms["camera"]["changed"] = True
    schedule_camera_commit()

def begin_camera_episode():
    camera = organisms["camera"]
    if camera["start_checkpoint"]:
        return
    camera["start_checkpoint"] = snapshot_state()
    camera["changed"] = False

def schedule_camera_commit():
    root = widgets.get("root")
    if not root:
        return
    camera = organisms["camera"]
    if camera["timer_id"]:
        root.after_cancel(camera["timer_id"])
    camera["timer_id"] = root.after(camera["window_ms"], on_camera_timer)

def on_camera_timer():
    organisms["camera"]["timer_id"] = None
    commit_camera_episode()

def commit_camera_episode():
    root = widgets.get("root")
    camera = organisms["camera"]
    if root and camera["timer_id"]:
        root.after_cancel(camera["timer_id"])
    camera["timer_id"] = None
    if camera["changed"] and camera["start_checkpoint"]:
        emit_event({"type": "COMMIT_CAMERA", "checkpoint": camera["start_checkpoint"]})
        pump_events()
        if "canvas" in widgets:
            refresh_projection()
    camera["start_checkpoint"] = None
    camera["changed"] = False

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
        reset_chord_organism()
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

    if kind == "UNDO":
        effects.append({"type": "HISTORY_UNDO"})
        return

    if kind == "REDO":
        effects.append({"type": "HISTORY_REDO"})
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

    if kind == "PREVIEW_NODE":
        effects.append({
            "type": "WORLD_UPDATE_NODE",
            "id": event["id"],
            "fields": event["fields"],
            "checkpoint": False,
        })
        return

    if kind == "COMMIT_DRAG":
        effects.append({"type": "HISTORY_REMEMBER", "checkpoint": event["checkpoint"], "label": "Drag"})
        return

    if kind == "COMMIT_CAMERA":
        effects.append({"type": "HISTORY_REMEMBER", "checkpoint": event["checkpoint"], "label": "Camera"})
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
        effects.append({"type": "HISTORY_REMEMBER", "checkpoint": snapshot_state(), "label": "New"})
        workspace["selected"] = None
        workspace["mode"] = None
        workspace["awaiting_click_for"] = None
        reset_camera()
        effects.append({"type": "WORLD_NEW"})
        effects.append({"type": "CONTINUITY_RESET"})
        effects.append({"type": "INSPECTOR_REFRESH"})
        effects.append({"type": "STATUS", "text": "New project"})
        return

    if kind == "LOAD_PROJECT":
        effects.append({"type": "HISTORY_REMEMBER", "checkpoint": snapshot_state(), "label": "Load"})
        workspace["selected"] = None
        workspace["mode"] = None
        workspace["awaiting_click_for"] = None
        load_camera(event["data"])
        effects.append({"type": "WORLD_LOAD", "data": event["data"]})
        effects.append({"type": "CONTINUITY_RESET"})
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
    if code == "UU":
        effects.append({"type": "HISTORY_UNDO"})
        return
    if code == "RR":
        effects.append({"type": "HISTORY_REDO"})
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
        remember_current("Create")
        node = create_node(effect["kind"], effect["x"], effect["y"])
        emit_event({"type": "SET_SELECTION", "id": node["id"]})
        effects.append({"type": "STATUS", "text": "Created " + node["kind"] + " " + node["id"]})
        return

    if kind == "WORLD_DELETE_NODE":
        if not find_node(effect["id"]):
            return
        remember_current("Delete")
        delete_node(effect["id"])
        emit_event({"type": "SET_SELECTION", "id": None})
        effects.append({"type": "STATUS", "text": "Object deleted"})
        return

    if kind == "WORLD_CLONE_NODE":
        if not find_node(effect["id"]):
            return
        remember_current("Clone")
        node = clone_node(effect["id"])
        if node:
            emit_event({"type": "SET_SELECTION", "id": node["id"]})
            effects.append({"type": "STATUS", "text": "Object cloned"})
        return

    if kind == "WORLD_UPDATE_NODE":
        if not find_node(effect["id"]):
            return
        if effect.get("checkpoint", True):
            remember_current("Update")
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

    if kind == "HISTORY_REMEMBER":
        remember_snapshot(effect["checkpoint"], effect["label"])
        return

    if kind == "HISTORY_UNDO":
        restore_undo()
        return

    if kind == "HISTORY_REDO":
        restore_redo()
        return

    if kind == "CONTINUITY_RESET":
        reset_continuity_for_time_jump()
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
    if "var_id" not in widgets:
        return
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
    if "status" not in widgets:
        return
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
        "world": snapshot_world(),
    }

def snapshot_workspace():
    return {
        "selected": workspace["selected"],
        "mode": workspace["mode"],
        "awaiting_click_for": workspace["awaiting_click_for"],
        "camera": {
            "scale": workspace["camera"]["scale"],
            "ox": workspace["camera"]["ox"],
            "oy": workspace["camera"]["oy"],
        },
    }

def snapshot_world():
    return {
        "next_id": world["next_id"],
        "nodes": [copy_node(node) for node in world["nodes"]],
    }

def restore_snapshot(snapshot):
    g["restoring_history"] = True
    try:
        workspace["selected"] = snapshot["workspace"]["selected"]
        workspace["mode"] = snapshot["workspace"]["mode"]
        workspace["awaiting_click_for"] = snapshot["workspace"]["awaiting_click_for"]
        workspace["camera"]["scale"] = snapshot["workspace"]["camera"]["scale"]
        workspace["camera"]["ox"] = snapshot["workspace"]["camera"]["ox"]
        workspace["camera"]["oy"] = snapshot["workspace"]["camera"]["oy"]

        world["next_id"] = snapshot["world"]["next_id"]
        world["nodes"].clear()
        for node in snapshot["world"]["nodes"]:
            world["nodes"].append(copy_node(node))

        reset_continuity_for_time_jump()
    finally:
        g["restoring_history"] = False

def reset_continuity_for_time_jump():
    derived.clear()
    tokenizer_state["drag_anchor_sx"] = raw["current"]["sx"]
    tokenizer_state["drag_anchor_sy"] = raw["current"]["sy"]
    judge_clear()
    reset_chord_organism()
    reset_move_organism()
    reset_rotate_organism()
    reset_camera_organisms()

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
