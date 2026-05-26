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
# CONTINUITY: RAW / TOKENIZERS / ORGANISMS
# -----------------------

def on_canvas_enter(e):
    raw_update_pointer(e)
    raw["current"]["inside_canvas"] = True
    g["canvas_hot"] = True
    raw["current"]["last_event_kind"] = "enter"
    if not focus_is_text_widget():
        focus_canvas()
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
    if e.keysym == "Escape":
        raw_set_key(e.keysym, True)
        raw["current"]["last_event_kind"] = "key_press"
        raw["current"]["last_key"] = e.keysym
        run_app_cycle()
        focus_canvas()
        return "break"
    if should_capture_chord(e.keysym):
        raw_set_key(e.keysym, True)
        raw["current"]["last_event_kind"] = "key_press"
        raw["current"]["last_key"] = e.keysym
        run_app_cycle()
        return "break"
    if focus_is_text_widget():
        return None
    raw_set_key(e.keysym, True)
    raw["current"]["last_event_kind"] = "key_press"
    raw["current"]["last_key"] = e.keysym
    run_app_cycle()

def on_keyup(e):
    if is_chord_key(e.keysym) and should_capture_chord(e.keysym):
        raw_set_key(e.keysym, False)
        raw["current"]["last_event_kind"] = "key_release"
        raw["current"]["last_key"] = e.keysym
        run_app_cycle()
        return "break"
    if focus_is_text_widget():
        return None
    raw_set_key(e.keysym, False)
    raw["current"]["last_event_kind"] = "key_release"
    raw["current"]["last_key"] = e.keysym
    run_app_cycle()

def on_left_press(e):
    focus_canvas()
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

def on_middle_press(e):
    focus_canvas()
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

def focus_canvas():
    if "canvas" in widgets:
        widgets["canvas"].focus_set()

def focus_is_text_widget():
    root = widgets.get("root")
    if not root:
        return False
    focus = root.focus_get()
    if not focus:
        return False
    return focus.winfo_class() in ("Entry", "TEntry", "Text", "Spinbox", "TSpinbox")

def is_chord_key(keysym):
    if not keysym:
        return False
    key = keysym.lower()
    if key == "space":
        key = " "
    return key in CHORD_BITS

def should_capture_chord(keysym=None):
    if keysym and not is_chord_key(keysym):
        return False
    if focus_is_text_widget():
        return False
    root = widgets.get("root")
    if not root:
        return False
    return root.focus_get() == widgets.get("canvas")

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
    if not judge_resources_match_context(resources):
        return False
    for resource in resources:
        if judge_is_context_resource(resource):
            continue
        current_owner = judge_owner(resource)
        if current_owner and current_owner != owner:
            return False
    return True

def judge_commit(owner, resources):
    if not judge_check(owner, resources):
        return False
    for resource in resources:
        if judge_is_context_resource(resource):
            continue
        judge["owners"][resource] = owner
    return True

def judge_resources_match_context(resources):
    for resource in resources:
        if not judge_resource_matches_context(resource):
            return False
    return True

def judge_resource_matches_context(resource):
    if resource == "mode:neutral":
        return workspace["mode"] is None and workspace["awaiting_click_for"] is None
    if resource == "mode:create_object":
        return workspace["mode"] in ("create_rect", "create_circle") and workspace["awaiting_click_for"] is None
    if resource == "mode:rotate_object":
        return workspace["mode"] == "rotate_object" and workspace["awaiting_click_for"] is None
    if resource == "mode:awaiting_target":
        return bool(workspace["awaiting_click_for"])
    if resource == "selection:primary":
        return bool(selection_primary())
    return True

def judge_is_context_resource(resource):
    return resource.startswith("mode:") or resource == "selection:primary"

def judge_release(owner):
    remove = []
    for resource in judge["owners"]:
        if judge["owners"][resource] == owner:
            remove.append(resource)
    for resource in remove:
        del judge["owners"][resource]

def judge_owner(resource):
    return judge["owners"].get(resource)

def emit_immediate(immediate):
    immediates.append(immediate)

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

def reset_drag_selection_organism():
    organisms["drag_selection"]["state"] = "idle"
    organisms["drag_selection"]["armed"] = False
    organisms["drag_selection"]["node_id"] = None
    organisms["drag_selection"]["ids"][:] = []
    organisms["drag_selection"]["start_positions"].clear()
    organisms["drag_selection"]["start_checkpoint"] = None
    organisms["drag_selection"]["changed"] = False

def reset_rotate_organism():
    organisms["rotate"]["state"] = "idle"
    organisms["rotate"]["pointer"] = None
    organisms["rotate"]["node_id"] = None
    organisms["rotate"]["start_checkpoint"] = None
    organisms["rotate"]["start_angle"] = None
    organisms["rotate"]["changed"] = False

def reset_camera_organisms():
    cancel_timer("camera")
    organisms["camera"]["start_checkpoint"] = None
    organisms["camera"]["changed"] = False
    organisms["camera_pan"]["state"] = "idle"
    organisms["camera_pan"]["last"] = None
    judge_release("camera_pan")

def reset_marquee_organism():
    organisms["marquee_select"]["state"] = "idle"
    organisms["marquee_select"]["start_sx"] = None
    organisms["marquee_select"]["start_sy"] = None
    organisms["marquee_select"]["current_sx"] = None
    organisms["marquee_select"]["current_sy"] = None
    organisms["marquee_select"]["start_wx"] = None
    organisms["marquee_select"]["start_wy"] = None
    organisms["marquee_select"]["current_wx"] = None
    organisms["marquee_select"]["current_wy"] = None
    organisms["marquee_select"]["candidate_ids"][:] = []
    judge_release("marquee_select")

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
        "start_sx": tokenizer_state["drag_anchor_sx"],
        "start_sy": tokenizer_state["drag_anchor_sy"],
        "current_sx": pointer["sx"],
        "current_sy": pointer["sy"],
        "start_wx": screen_to_world(tokenizer_state["drag_anchor_sx"], tokenizer_state["drag_anchor_sy"])[0],
        "start_wy": screen_to_world(tokenizer_state["drag_anchor_sx"], tokenizer_state["drag_anchor_sy"])[1],
        "current_wx": pointer["wx"],
        "current_wy": pointer["wy"],
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
    run_drag_selection_organism()
    run_marquee_select_organism()
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
    if not derived["buttons"]["b1_pressed"]:
        return
    if not judge_commit("awaiting_target", ["mode:awaiting_target", "pointer:left", "selection"]):
        return
    emit_event({
        "type": "COMMAND_TARGETED",
        "code": workspace["awaiting_click_for"],
        "id": derived["target"]["node_id"],
    })
    judge_release("awaiting_target")

def run_create_object_organism():
    if not derived["buttons"]["b1_pressed"]:
        return
    if not judge_commit("create_object", ["mode:create_object", "pointer:left"]):
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
    if not judge_commit("click_selection", ["mode:neutral", "pointer:left", "selection"]):
        return
    emit_event({"type": "SET_SELECTION", "id": derived["target"]["node_id"]})
    judge_release("click_selection")

def run_drag_selection_organism():
    drag = organisms["drag_selection"]
    if drag["state"] == "idle":
        start_drag_selection_organism()
        return
    if drag["state"] == "armed":
        update_armed_drag_selection()
        return
    if drag["state"] == "active":
        update_active_drag_selection()

def start_drag_selection_organism():
    if not derived["buttons"]["b1_pressed"]:
        return
    nid = derived["target"]["node_id"]
    if not nid:
        return
    if not judge_commit("drag_selection", ["mode:neutral", "pointer:left", "selection"]):
        return
    if not selection_has(nid):
        emit_event({"type": "SET_SELECTION", "id": nid})
        ids = [nid]
    else:
        ids = selection_ids()
    drag = organisms["drag_selection"]
    drag["state"] = "armed"
    drag["armed"] = True
    drag["node_id"] = nid
    drag["ids"][:] = ids
    drag["start_positions"].clear()
    for node_id in ids:
        node = find_node(node_id)
        if node:
            drag["start_positions"][node_id] = {"x": node["x"], "y": node["y"]}
    drag["start_checkpoint"] = snapshot_state()
    drag["changed"] = False

def update_armed_drag_selection():
    drag = organisms["drag_selection"]
    if derived["buttons"]["b1_released"]:
        reset_drag_selection_organism()
        judge_release("drag_selection")
        return
    if not derived["drag"]["threshold_crossed"]:
        return
    drag["state"] = "active"
    update_drag_selection_preview()

def update_active_drag_selection():
    if derived["buttons"]["b1_released"]:
        update_drag_selection_preview()
        stop_drag_selection_organism()
        return
    update_drag_selection_preview()

def update_drag_selection_preview():
    drag = organisms["drag_selection"]
    updates = current_drag_selection_updates()
    if updates:
        emit_immediate({"type": "NODE_PREVIEW_MAP", "updates": updates})
        drag["changed"] = True

def stop_drag_selection_organism():
    drag = organisms["drag_selection"]
    if drag["changed"]:
        updates = current_drag_selection_updates()
        undo_delta, redo_delta = build_drag_delta(drag["start_positions"], updates)
        emit_event({
            "type": "COMMIT_DRAG",
            "checkpoint": drag["start_checkpoint"],
            "updates": updates,
            "undo_delta": undo_delta,
            "redo_delta": redo_delta,
        })
    reset_drag_selection_organism()
    judge_release("drag_selection")

def current_drag_selection_updates():
    drag = organisms["drag_selection"]
    dx = derived["pointer"]["wx"] - derived["drag"]["start_wx"]
    dy = derived["pointer"]["wy"] - derived["drag"]["start_wy"]
    updates = {}
    for nid in drag["ids"]:
        start = drag["start_positions"].get(nid)
        if start:
            updates[nid] = {"x": start["x"] + dx, "y": start["y"] + dy}
    return updates

def build_drag_delta(start_positions, updates):
    undo_delta = []
    redo_delta = []
    for nid in start_positions:
        if nid in updates:
            undo_delta.append({"op": "update_node", "id": nid, "fields": copy_fields(start_positions[nid], ("x", "y"))})
            redo_delta.append({"op": "update_node", "id": nid, "fields": updates[nid]})
    return undo_delta, redo_delta

def run_rotate_object_organism():
    rotate = organisms["rotate"]
    if rotate["state"] == "idle":
        start_rotate_organism()
        return
    if rotate["state"] == "active":
        update_rotate_organism()

def start_rotate_organism():
    selected = selection_primary()
    if not selected:
        return
    if not derived["buttons"]["b1_pressed"]:
        return
    if not judge_commit("rotate_object", ["mode:rotate_object", "selection:primary", "pointer:left", "selection", "node:" + selected]):
        return
    rotate = organisms["rotate"]
    rotate["state"] = "active"
    rotate["pointer"] = "left"
    rotate["node_id"] = selected
    rotate["start_checkpoint"] = snapshot_state()
    rotate["start_angle"] = find_node(selected)["angle"]
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
    angle = current_rotate_angle(node)
    emit_immediate({"type": "NODE_PREVIEW", "id": node["id"], "fields": {"angle": angle}})
    rotate["changed"] = True

def stop_rotate_organism():
    rotate = organisms["rotate"]
    if rotate["changed"]:
        node = find_node(rotate["node_id"])
        undo_delta = []
        redo_delta = []
        updates = {}
        if node:
            angle = current_rotate_angle(node)
            updates[node["id"]] = {"angle": angle}
            undo_delta.append({"op": "update_node", "id": node["id"], "fields": {"angle": rotate["start_angle"]}})
            redo_delta.append({"op": "update_node", "id": node["id"], "fields": {"angle": angle}})
        emit_event({
            "type": "COMMIT_DRAG",
            "checkpoint": rotate["start_checkpoint"],
            "updates": updates,
            "undo_delta": undo_delta,
            "redo_delta": redo_delta,
        })
    reset_rotate_organism()
    judge_release("rotate_object")

def current_rotate_angle(node):
    return math.degrees(math.atan2(derived["pointer"]["wy"] - node["y"], derived["pointer"]["wx"] - node["x"]))

def run_marquee_select_organism():
    marquee = organisms["marquee_select"]
    if marquee["state"] == "idle":
        start_marquee_select_organism()
        return
    if marquee["state"] == "armed":
        update_armed_marquee()
        return
    if marquee["state"] == "active":
        update_active_marquee()

def start_marquee_select_organism():
    if not derived["buttons"]["b1_pressed"]:
        return
    if derived["target"]["node_id"]:
        return
    if not judge_commit("marquee_select", ["mode:neutral", "pointer:left", "selection-preview"]):
        return
    marquee = organisms["marquee_select"]
    marquee["state"] = "armed"
    marquee["start_sx"] = derived["drag"]["start_sx"]
    marquee["start_sy"] = derived["drag"]["start_sy"]
    marquee["current_sx"] = derived["drag"]["current_sx"]
    marquee["current_sy"] = derived["drag"]["current_sy"]
    marquee["start_wx"] = derived["drag"]["start_wx"]
    marquee["start_wy"] = derived["drag"]["start_wy"]
    marquee["current_wx"] = derived["drag"]["current_wx"]
    marquee["current_wy"] = derived["drag"]["current_wy"]
    marquee["candidate_ids"][:] = []

def update_armed_marquee():
    marquee = organisms["marquee_select"]
    if derived["drag"]["threshold_crossed"]:
        marquee["state"] = "active"
        update_marquee_rect()
        if derived["buttons"]["b1_released"]:
            commit_marquee_selection()
        return
    if derived["buttons"]["b1_released"]:
        emit_event({"type": "SET_SELECTION", "ids": [], "primary": None})
        reset_marquee_organism()

def update_active_marquee():
    if derived["buttons"]["b1_released"]:
        update_marquee_rect()
        commit_marquee_selection()
        return
    update_marquee_rect()

def commit_marquee_selection():
    marquee = organisms["marquee_select"]
    ids = list(marquee["candidate_ids"])
    primary = ids[0] if ids else None
    emit_event({"type": "SET_SELECTION", "ids": ids, "primary": primary})
    reset_marquee_organism()

def update_marquee_rect():
    marquee = organisms["marquee_select"]
    marquee["current_sx"] = derived["drag"]["current_sx"]
    marquee["current_sy"] = derived["drag"]["current_sy"]
    marquee["current_wx"] = derived["drag"]["current_wx"]
    marquee["current_wy"] = derived["drag"]["current_wy"]
    ids = selection_candidates_in_world_rect(
        marquee["start_wx"],
        marquee["start_wy"],
        marquee["current_wx"],
        marquee["current_wy"],
    )
    marquee["candidate_ids"][:] = ids
    emit_immediate({
        "type": "MARQUEE_PREVIEW",
        "start_sx": marquee["start_sx"],
        "start_sy": marquee["start_sy"],
        "current_sx": marquee["current_sx"],
        "current_sy": marquee["current_sy"],
        "candidate_ids": list(ids),
    })

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
        emit_immediate({"type": "CURSOR", "cursor": "fleur"})
        return
    if pan["state"] == "active":
        if derived["buttons"]["b2_released"]:
            schedule_camera_commit()
            pan["state"] = "idle"
            pan["last"] = None
            judge_release("camera_pan")
            return
        emit_immediate({"type": "CURSOR", "cursor": "fleur"})
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
