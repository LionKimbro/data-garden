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
# WORLD MODEL
# -----------------------

def create_node(kind, x, y):
    fill = "#6d4c41"
    w = 140
    h = 100
    title = ""
    zoom_min = 0.0
    zoom_max = 999999.0
    if kind == "circle":
        fill = "#3a6ea5"
        w = 120
        h = 120
    if kind == "text":
        fill = TEXT_DEFAULT_FILL
        w = TEXT_DEFAULT_W
        h = TEXT_DEFAULT_H
        title = "Text"
        zoom_min, zoom_max = text_zoom_range_for_current_camera()

    node = {
        "id": gen_id(),
        "kind": kind,
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "angle": 0.0,
        "fill": fill,
        "title": title,
        "url": "",
        "note": "",
        "zoom_min": zoom_min,
        "zoom_max": zoom_max,
    }
    world["nodes"].append(node)
    return node

def text_zoom_range_for_current_camera():
    scale = float(workspace["camera"]["scale"])
    zoom_min = max(ZOOM_VISIBILITY_MIN, scale / TEXT_ZOOM_SPAN_FACTOR)
    zoom_max = min(ZOOM_VISIBILITY_MAX, scale * TEXT_ZOOM_SPAN_FACTOR)
    if zoom_max < zoom_min:
        zoom_max = zoom_min
    return zoom_min, zoom_max

def node_visible_at_current_zoom(node):
    if node["kind"] != "text":
        return True
    scale = float(workspace["camera"]["scale"])
    zoom_min = float(node.get("zoom_min", 0.0))
    zoom_max = float(node.get("zoom_max", 999999.0))
    return zoom_min <= scale <= zoom_max

def node_allows_manipulation(node):
    return node and node["kind"] in ("rect", "circle")

def selection_allows_manipulation():
    ids = selection_ids()
    if not ids:
        return False
    for nid in ids:
        node = find_node(nid)
        if not node_allows_manipulation(node):
            return False
    return True

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

def clone_nodes(ids):
    clones = []
    for nid in ids:
        node = clone_node(nid)
        if node:
            clones.append(node)
    return clones

def delete_node(nid):
    world["nodes"][:] = [node for node in world["nodes"] if node["id"] != nid]

def delete_nodes(ids):
    world["nodes"][:] = [node for node in world["nodes"] if node["id"] not in ids]

def update_node(nid, fields):
    node = find_node(nid)
    if not node:
        return
    for key in fields:
        if key in NODE_KEYS and key != "id":
            node[key] = fields[key]

def update_nodes(ids, fields):
    for nid in ids:
        update_node(nid, fields)

def update_node_map(updates):
    for nid in updates:
        update_node(nid, updates[nid])

def find_node(nid):
    for node in world["nodes"]:
        if node["id"] == nid:
            return node
    return None

def existing_ids(ids):
    found = []
    for nid in ids:
        if find_node(nid) and nid not in found:
            found.append(nid)
    return found

def node_index(nid):
    for i in range(len(world["nodes"])):
        if world["nodes"][i]["id"] == nid:
            return i
    return None

def copy_fields(source, keys):
    fields = {}
    for key in keys:
        fields[key] = source[key]
    return fields

def build_update_delta(ids, fields):
    undo_delta = []
    redo_delta = []
    keys = list(fields.keys())
    for nid in ids:
        node = find_node(nid)
        if node:
            undo_delta.append({"op": "update_node", "id": nid, "fields": copy_fields(node, keys)})
            redo_delta.append({"op": "update_node", "id": nid, "fields": copy_fields(fields, keys)})
    return undo_delta, redo_delta

def build_update_map_delta(updates):
    undo_delta = []
    redo_delta = []
    for nid in updates:
        node = find_node(nid)
        if node:
            keys = list(updates[nid].keys())
            undo_delta.append({"op": "update_node", "id": nid, "fields": copy_fields(node, keys)})
            redo_delta.append({"op": "update_node", "id": nid, "fields": copy_fields(updates[nid], keys)})
    return undo_delta, redo_delta

def update_map_changed(updates):
    for nid in updates:
        node = find_node(nid)
        if node:
            for key in updates[nid]:
                if node[key] != updates[nid][key]:
                    return True
    return False

def dump_world_packet():
    return {
        "nodes": [copy_node(node) for node in world["nodes"]],
        "next_id": world["next_id"],
    }

def make_world_revision_guid():
    world["revision_serial"] += 1
    return "world-rev-" + str(world["revision_serial"]).zfill(6)

def reset_world_revisions(label):
    world["current_revision_guid"] = "world-rev-000000"
    world["revision_serial"] = 0
    world["revisions"].clear()
    world["revisions"]["world-rev-000000"] = {
        "guid": "world-rev-000000",
        "parent": None,
        "label": label,
        "undo_delta": [],
        "redo_delta": [],
    }

def record_world_revision(label, undo_delta, redo_delta):
    if not undo_delta and not redo_delta:
        return world["current_revision_guid"]
    guid = make_world_revision_guid()
    world["revisions"][guid] = {
        "guid": guid,
        "parent": world["current_revision_guid"],
        "label": label,
        "undo_delta": copy_delta(undo_delta),
        "redo_delta": copy_delta(redo_delta),
    }
    world["current_revision_guid"] = guid
    return guid

def copy_delta(delta):
    copied = []
    for note in delta:
        copied.append(copy_delta_note(note))
    return copied

def copy_delta_note(note):
    copied = {}
    for key in note:
        if key == "node":
            copied[key] = copy_node(note[key])
        elif key == "nodes":
            copied[key] = [copy_node(node) for node in note[key]]
        elif key == "fields":
            fields = {}
            for field in note[key]:
                fields[field] = note[key][field]
            copied[key] = fields
        else:
            copied[key] = note[key]
    return copied

def apply_world_delta(delta):
    for note in delta:
        apply_delta_note(note)

def apply_delta_note(note):
    op = note["op"]
    if op == "create_node":
        delete_node(note["node"]["id"])
        world["nodes"].append(copy_node(note["node"]))
        repair_next_id()
        return
    if op == "delete_node":
        delete_node(note["id"])
        return
    if op == "restore_node":
        delete_node(note["node"]["id"])
        index = note.get("index")
        node = copy_node(note["node"])
        if index is None or index >= len(world["nodes"]):
            world["nodes"].append(node)
        else:
            world["nodes"].insert(index, node)
        repair_next_id()
        return
    if op == "update_node":
        update_node(note["id"], note["fields"])
        return
    if op == "replace_world":
        world["nodes"].clear()
        for node in note["nodes"]:
            world["nodes"].append(copy_node(node))
        world["next_id"] = note["next_id"]
        repair_next_id()

def goto_world_revision(guid):
    if guid == world["current_revision_guid"]:
        return
    current_path = world_path_to_root(world["current_revision_guid"])
    target_path = world_path_to_root(guid)
    common = find_common_revision(current_path, target_path)

    current = world["current_revision_guid"]
    while current != common:
        revision = world["revisions"][current]
        apply_world_delta(revision["undo_delta"])
        current = revision["parent"]
        world["current_revision_guid"] = current

    forward = []
    target = guid
    while target != common:
        forward.append(target)
        target = world["revisions"][target]["parent"]
    for rev_guid in reversed(forward):
        apply_world_delta(world["revisions"][rev_guid]["redo_delta"])
        world["current_revision_guid"] = rev_guid

def world_path_to_root(guid):
    path = []
    current = guid
    while current:
        path.append(current)
        current = world["revisions"][current]["parent"]
    return path

def find_common_revision(path_a, path_b):
    seen = set(path_a)
    for guid in path_b:
        if guid in seen:
            return guid
    return "world-rev-000000"

def node_bounds_world(node):
    if node["kind"] == "circle":
        return (
            node["x"] - node["w"] / 2,
            node["y"] - node["h"] / 2,
            node["x"] + node["w"] / 2,
            node["y"] + node["h"] / 2,
        )
    if node["kind"] in ("rect", "text"):
        points = rect_points_world(node)
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return (min(xs), min(ys), max(xs), max(ys))
    return None

def rect_points_world(node):
    angle = math.radians(node["angle"])
    dx = node["w"] / 2
    dy = node["h"] / 2
    corners = [(-dx, -dy), (dx, -dy), (dx, dy), (-dx, dy)]
    points = []
    cs = math.cos(angle)
    sn = math.sin(angle)
    for x, y in corners:
        rx = x * cs - y * sn
        ry = x * sn + y * cs
        points.append((node["x"] + rx, node["y"] + ry))
    return points

def rect_bounds_from_points(x0, y0, x1, y1):
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

def rects_intersect(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])

def selection_candidates_in_world_rect(x0, y0, x1, y1):
    bounds = rect_bounds_from_points(x0, y0, x1, y1)
    ids = []
    for node in world["nodes"]:
        if not node_visible_at_current_zoom(node):
            continue
        node_bounds = node_bounds_world(node)
        if node_bounds and rects_intersect(bounds, node_bounds):
            ids.append(node["id"])
    return ids

def selected_bounds_world():
    bounds = []
    for nid in selection_ids():
        node = find_node(nid)
        if node:
            node_bounds = node_bounds_world(node)
            if node_bounds:
                bounds.append(node_bounds)
    if not bounds:
        return None
    return (
        min(item[0] for item in bounds),
        min(item[1] for item in bounds),
        max(item[2] for item in bounds),
        max(item[3] for item in bounds),
    )

def center_of_bounds(bounds):
    return ((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2)

def distance(a, b):
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return math.sqrt(dx * dx + dy * dy)

def angle_from(pivot, point):
    return math.degrees(math.atan2(point[1] - pivot[1], point[0] - pivot[0]))

def rotate_point(point, pivot, degrees):
    radians = math.radians(degrees)
    cs = math.cos(radians)
    sn = math.sin(radians)
    dx = point[0] - pivot[0]
    dy = point[1] - pivot[1]
    return (pivot[0] + dx * cs - dy * sn, pivot[1] + dx * sn + dy * cs)

def transform_nodes_for_rotation(originals, ids, pivot, delta):
    updates = {}
    for nid in ids:
        original = originals.get(nid)
        if original:
            x, y = rotate_point((original["x"], original["y"]), pivot, delta)
            updates[nid] = {
                "x": x,
                "y": y,
                "angle": original["angle"] + delta,
            }
    return updates

def transform_nodes_for_scale(originals, ids, pivot, scale):
    updates = {}
    for nid in ids:
        original = originals.get(nid)
        if original:
            updates[nid] = {
                "x": pivot[0] + (original["x"] - pivot[0]) * scale,
                "y": pivot[1] + (original["y"] - pivot[1]) * scale,
                "w": original["w"] * scale,
                "h": original["h"] * scale,
            }
    return updates

def node_display_title(node):
    title = node["title"].strip()
    if not title and "text" in node:
        title = str(node["text"]).strip().splitlines()[0]
    if not title:
        title = node["id"]
    if len(title) > 60:
        title = title[:57] + "..."
    return title

def hover_status_for_node(node):
    title = node_display_title(node)
    if title == node["id"]:
        text = "Hover: " + node["id"] + "  (" + node["kind"] + ")"
    else:
        text = "Hover: " + title + "  (" + node["id"] + ", " + node["kind"] + ")"
    if node["url"].strip():
        text += " [link]"
    return text

def node_callout_title(node):
    title = node["title"].strip()
    if not title and "text" in node:
        title = str(node["text"]).strip().splitlines()[0]
    if not title:
        title = node["id"]
    title = " ".join(str(title).split())
    if len(title) > CALLOUT_MAX_TITLE_CHARS:
        title = title[:CALLOUT_MAX_TITLE_CHARS - 3] + "..."
    return title

def copy_node(node):
    copied = {}
    for key in NODE_KEYS:
        if key == "zoom_min":
            copied[key] = node.get(key, 0.0)
        elif key == "zoom_max":
            copied[key] = node.get(key, 999999.0)
        else:
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
