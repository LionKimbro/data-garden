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
        callouts_clear()
        workspace["mode"] = None
        workspace["awaiting_click_for"] = None
        reset_chord_organism()
        reset_rotate_selection_organism()
        reset_size_selection_organism()
        manipulation_hide()
        effects.append({"type": "STATUS", "text": "Ready"})
        return

    if kind == "SET_MODE":
        workspace["mode"] = event["mode"]
        effects.append({"type": "STATUS", "text": "Mode: " + str(event["mode"])})
        return

    if kind == "SET_SELECTION":
        callouts_clear()
        if "ids" in event:
            selection_set(event["ids"], event.get("primary"))
        else:
            selection_single(event["id"])
        if selection_ids():
            manipulation_show("size")
        else:
            manipulation_hide()
        effects.append({"type": "INSPECTOR_REFRESH"})
        return

    if kind == "TOGGLE_MANIPULATION":
        callouts_clear()
        manipulation_toggle()
        return

    if kind == "SHOW_SELECTION_CALLOUTS":
        effects.append({"type": "SHOW_SELECTION_CALLOUTS", "ids": event["ids"], "source": event.get("source", "marquee")})
        return

    if kind == "CLEAR_SELECTION_CALLOUTS":
        effects.append({"type": "CLEAR_SELECTION_CALLOUTS"})
        return

    if kind == "UNDO":
        effects.append({"type": "HISTORY_UNDO"})
        return

    if kind == "REDO":
        effects.append({"type": "HISTORY_REDO"})
        return

    if kind == "CREATE_NODE":
        callouts_clear()
        workspace["mode"] = None
        effects.append({
            "type": "WORLD_CREATE_NODE",
            "kind": event["kind"],
            "x": event["x"],
            "y": event["y"],
            "fields": event.get("fields", {}),
        })
        return

    if kind == "DELETE_NODE":
        callouts_clear()
        ids = event.get("ids")
        if ids is None:
            ids = [event["id"]]
        effects.append({"type": "WORLD_DELETE_NODES", "ids": ids})
        return

    if kind == "CLONE_NODE":
        callouts_clear()
        ids = event.get("ids")
        if ids is None:
            ids = [event["id"]]
        effects.append({"type": "WORLD_CLONE_NODES", "ids": ids})
        return

    if kind == "SET_NODE_FILL":
        callouts_clear()
        ids = event.get("ids")
        if ids is None:
            ids = [event["id"]]
        effects.append({"type": "WORLD_UPDATE_NODES", "ids": ids, "fields": {"fill": event["fill"]}})
        return

    if kind == "UPDATE_NODE":
        callouts_clear()
        effects.append({"type": "WORLD_UPDATE_NODE", "id": event["id"], "fields": event["fields"]})
        return

    if kind == "COMMIT_DRAG":
        if not event.get("undo_delta") and not event.get("redo_delta"):
            return
        effects.append({
            "type": "WORLD_UPDATE_NODE_MAP",
            "updates": event.get("updates", {}),
            "checkpoint": False,
        })
        effects.append({
            "type": "WORLD_RECORD_REVISION",
            "label": "Drag",
            "undo_delta": event.get("undo_delta", []),
            "redo_delta": event.get("redo_delta", []),
        })
        effects.append({"type": "HISTORY_REMEMBER", "checkpoint": event["checkpoint"], "label": "Drag"})
        return

    if kind == "COMMIT_CAMERA":
        effects.append({"type": "HISTORY_REMEMBER", "checkpoint": event["checkpoint"], "label": "Camera"})
        return

    if kind == "ROTATE_SELECTION":
        callouts_clear()
        effects.append({"type": "WORLD_UPDATE_NODE_MAP", "updates": event["updates"], "label": "Rotate"})
        effects.append({"type": "STATUS", "text": "Rotated selection"})
        return

    if kind == "SIZE_SELECTION":
        callouts_clear()
        effects.append({"type": "WORLD_UPDATE_NODE_MAP", "updates": event["updates"], "label": "Size"})
        effects.append({"type": "STATUS", "text": "Sized selection"})
        return

    if kind == "SET_CAMERA":
        workspace["camera"]["scale"] = event["scale"]
        workspace["camera"]["ox"] = event["ox"]
        workspace["camera"]["oy"] = event["oy"]
        return

    if kind == "OPEN_LINK":
        callouts_clear()
        effects.append({"type": "OPEN_LINK", "id": event["id"]})
        return

    if kind == "SAVE_FILE":
        callouts_clear()
        effects.append({"type": "SAVE_FILE"})
        return

    if kind == "NEW_PROJECT":
        callouts_clear()
        selection_clear()
        manipulation_hide()
        workspace["mode"] = None
        workspace["awaiting_click_for"] = None
        reset_camera()
        effects.append({"type": "WORLD_NEW"})
        effects.append({"type": "CONTINUITY_RESET"})
        effects.append({"type": "INSPECTOR_REFRESH"})
        effects.append({"type": "STATUS", "text": "New project"})
        return

    if kind == "LOAD_PROJECT":
        callouts_clear()
        selection_clear()
        manipulation_hide()
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
    if code == "CT":
        workspace["mode"] = "create_text"
        return
    if code == "PR":
        workspace["mode"] = "paste_rect"
        return
    if code == "PC":
        workspace["mode"] = "paste_circle"
        return
    if code == "PT":
        workspace["mode"] = "paste_text"
        return
    if code == "AA":
        callouts_clear()
        selection_clear()
        manipulation_hide()
        workspace["mode"] = None
        workspace["awaiting_click_for"] = None
        reset_rotate_selection_organism()
        reset_size_selection_organism()
        effects.append({"type": "INSPECTOR_REFRESH"})
        return
    if code == "UU":
        effects.append({"type": "HISTORY_UNDO"})
        return
    if code == "RR":
        effects.append({"type": "HISTORY_REDO"})
        return
    if code == "SF":
        effects.append({"type": "SAVE_FILE"})
        return

    reduce_object_command(code, selection_primary())

def reduce_command_targeted(event):
    code = event["code"]
    workspace["awaiting_click_for"] = None
    if not event["id"]:
        effects.append({"type": "STATUS", "text": code + " cancelled"})
        return
    selection_single(event["id"])
    effects.append({"type": "INSPECTOR_REFRESH"})
    reduce_object_command(code, event["id"])

def reduce_object_command(code, nid):
    if code == "CO":
        if nid:
            effects.append({"type": "ASK_COLOR", "ids": selection_ids()})
        else:
            workspace["awaiting_click_for"] = "CO"
            effects.append({"type": "STATUS", "text": "CO: click a node to color it, or click empty space to cancel"})
        return

    if code == "DO":
        if nid:
            effects.append({"type": "ASK_DELETE", "ids": selection_ids()})
        else:
            workspace["awaiting_click_for"] = "DO"
            effects.append({"type": "STATUS", "text": "DO: click a node to delete it, or click empty space to cancel"})
        return

    if code == "XO":
        if nid:
            effects.append({"type": "WORLD_CLONE_NODES", "ids": selection_ids()})
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
        fields = effect.get("fields", {})
        if fields:
            update_node(node["id"], fields)
        record_world_revision(
            "Create",
            [{"op": "delete_node", "id": node["id"]}],
            [{"op": "create_node", "node": copy_node(node)}],
        )
        emit_event({"type": "SET_SELECTION", "id": node["id"]})
        effects.append({"type": "STATUS", "text": "Created " + node["kind"] + " " + node["id"]})
        return

    if kind == "WORLD_DELETE_NODES":
        ids = existing_ids(effect["ids"])
        if not ids:
            return
        remember_current("Delete")
        undo_delta = []
        redo_delta = []
        for nid in ids:
            node = find_node(nid)
            undo_delta.append({"op": "restore_node", "node": copy_node(node), "index": node_index(nid)})
            redo_delta.append({"op": "delete_node", "id": nid})
        delete_nodes(ids)
        if workspace["hover"]["id"] not in existing_ids([workspace["hover"]["id"]]):
            workspace["hover"]["id"] = None
            status_hover_clear()
        record_world_revision("Delete", undo_delta, redo_delta)
        emit_event({"type": "SET_SELECTION", "ids": [], "primary": None})
        effects.append({"type": "STATUS", "text": "Object deleted"})
        return

    if kind == "WORLD_CLONE_NODES":
        ids = existing_ids(effect["ids"])
        if not ids:
            return
        remember_current("Clone")
        clones = clone_nodes(ids)
        if clones:
            undo_delta = []
            redo_delta = []
            for node in clones:
                undo_delta.append({"op": "delete_node", "id": node["id"]})
                redo_delta.append({"op": "create_node", "node": copy_node(node)})
            record_world_revision("Clone", undo_delta, redo_delta)
            clone_ids = [node["id"] for node in clones]
            emit_event({"type": "SET_SELECTION", "ids": clone_ids, "primary": clone_ids[0]})
            effects.append({"type": "STATUS", "text": "Object cloned"})
        return

    if kind == "WORLD_UPDATE_NODES":
        ids = existing_ids(effect["ids"])
        if not ids:
            return
        if effect.get("checkpoint", True):
            remember_current("Update")
            undo_delta, redo_delta = build_update_delta(ids, effect["fields"])
        update_nodes(ids, effect["fields"])
        if effect.get("checkpoint", True):
            record_world_revision("Update", undo_delta, redo_delta)
        effects.append({"type": "INSPECTOR_REFRESH"})
        return

    if kind == "WORLD_UPDATE_NODE_MAP":
        ids = existing_ids(effect["updates"].keys())
        if not ids:
            return
        if not update_map_changed(effect["updates"]):
            return
        label = effect.get("label", "Update")
        if effect.get("checkpoint", True):
            remember_current(label)
            undo_delta, redo_delta = build_update_map_delta(effect["updates"])
        update_node_map(effect["updates"])
        if effect.get("checkpoint", True):
            record_world_revision(label, undo_delta, redo_delta)
        effects.append({"type": "INSPECTOR_REFRESH"})
        return

    if kind == "WORLD_UPDATE_NODE":
        if not find_node(effect["id"]):
            return
        if effect.get("checkpoint", True):
            remember_current("Update")
            undo_delta, redo_delta = build_update_delta([effect["id"]], effect["fields"])
        update_node(effect["id"], effect["fields"])
        if effect.get("checkpoint", True):
            record_world_revision("Update", undo_delta, redo_delta)
        effects.append({"type": "INSPECTOR_REFRESH"})
        return

    if kind == "WORLD_NEW":
        workspace["hover"]["id"] = None
        status_hover_clear()
        reset_world()
        reset_world_revisions("New")
        clear_history()
        g["filepath"] = None
        return

    if kind == "WORLD_LOAD":
        workspace["hover"]["id"] = None
        status_hover_clear()
        load_world(effect["data"])
        reset_world_revisions("Load")
        clear_history()
        return

    if kind == "WORLD_RECORD_REVISION":
        record_world_revision(effect["label"], effect["undo_delta"], effect["redo_delta"])
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
        ask_color(effect["ids"])
        return

    if kind == "ASK_DELETE":
        ask_delete(effect["ids"])
        return

    if kind == "OPEN_LINK":
        open_node_link(effect["id"])
        return

    if kind == "SAVE_FILE":
        file_save()
        return

    if kind == "SHOW_SELECTION_CALLOUTS":
        callouts_show(existing_ids(effect["ids"]), effect.get("source", "marquee"))
        return

    if kind == "CLEAR_SELECTION_CALLOUTS":
        callouts_clear()
        return

def ask_color(ids):
    ids = existing_ids(ids)
    if not ids:
        return
    node = find_node(ids[0])
    if not node:
        return
    choice = colorchooser.askcolor(color=node["fill"], title="Pick Fill Color")
    if choice and choice[1]:
        emit_event({"type": "SET_NODE_FILL", "ids": ids, "fill": choice[1]})
        pump_events()
        refresh_projection()

def ask_delete(ids):
    ids = existing_ids(ids)
    if not ids:
        return
    if messagebox.askyesno("Delete", "Delete selected object?"):
        emit_event({"type": "DELETE_NODE", "ids": ids})
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
