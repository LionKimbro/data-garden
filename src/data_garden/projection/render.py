import json
import math
import os
import shutil
import tempfile
import webbrowser
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, colorchooser, messagebox

from data_garden.constants import *
from data_garden.state import *

# -----------------------
# PROJECTION
# -----------------------

def refresh_projection():
    realize_camera()
    apply_cursor_immediates()
    draw_grid()
    draw_nodes()
    draw_selection()
    draw_manipulation_frame()
    draw_marquee()
    draw_callouts()

def apply_cursor_immediates():
    if "canvas" not in widgets:
        return
    cursor = "arrow"
    for immediate in reversed(immediates):
        if immediate["type"] == "CURSOR":
            cursor = immediate["cursor"]
            break
    widgets["canvas"].config(cursor=cursor)

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
        if not node_visible_at_current_zoom(node):
            continue
        item = draw_node(projected_node_from_node(node))
        if item:
            projection["items"][item] = node["id"]

def draw_node(node):
    if node["kind"] == "rect":
        return draw_rect_node(node)
    if node["kind"] == "circle":
        return draw_circle_node(node)
    if node["kind"] == "text":
        return draw_text_node(node)
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

def draw_text_node(node):
    canvas = widgets["canvas"]
    sx, sy = world_to_screen(node["x"], node["y"])
    return canvas.create_text(
        sx,
        sy,
        text=node["title"] or node["id"],
        fill=node["fill"],
        anchor="center",
        angle=-node["angle"],
        tags=("node", "n:" + node["id"]),
    )

def draw_selection():
    canvas = widgets["canvas"]
    canvas.delete("sel")
    for nid in selection_ids():
        draw_node_selection(nid)

def draw_manipulation_frame():
    canvas = widgets["canvas"]
    canvas.delete("manipulation")
    if not workspace["manipulation"]["visible"]:
        return
    if not selection_ids():
        return
    bounds = selected_bounds_world()
    if not bounds:
        return
    points = frame_points_screen(bounds)
    canvas.create_rectangle(
        points["nw"][0],
        points["nw"][1],
        points["se"][0],
        points["se"][1],
        outline=MANIPULATION_FRAME_OUTLINE,
        width=1,
        dash=(5, 3),
        tags=("manipulation",),
    )
    if workspace["manipulation"]["kind"] == "rotate":
        draw_rotate_handle(points)
    if workspace["manipulation"]["kind"] == "size":
        draw_size_handles()

def draw_rotate_handle(points):
    canvas = widgets["canvas"]
    top_x, top_y = points["n"]
    for spec in handle_specs_for_selection():
        canvas.create_line(
            top_x,
            top_y,
            spec["sx"],
            spec["sy"],
            fill=MANIPULATION_FRAME_OUTLINE,
            width=1,
            tags=("manipulation",),
        )
        r = spec["radius"]
        canvas.create_oval(
            spec["sx"] - r,
            spec["sy"] - r,
            spec["sx"] + r,
            spec["sy"] + r,
            fill=ROTATE_HANDLE_FILL,
            outline=HANDLE_OUTLINE,
            width=1,
            tags=("manipulation",),
        )

def draw_size_handles():
    canvas = widgets["canvas"]
    for spec in handle_specs_for_selection():
        r = spec["radius"]
        canvas.create_rectangle(
            spec["sx"] - r,
            spec["sy"] - r,
            spec["sx"] + r,
            spec["sy"] + r,
            fill=SIZE_HANDLE_FILL,
            outline=HANDLE_OUTLINE,
            width=1,
            tags=("manipulation",),
        )

def draw_marquee():
    canvas = widgets["canvas"]
    canvas.delete("marquee")
    marquee = current_marquee_preview()
    if not marquee:
        return
    x0 = marquee["start_sx"]
    y0 = marquee["start_sy"]
    x1 = marquee["current_sx"]
    y1 = marquee["current_sy"]
    canvas.create_rectangle(
        x0,
        y0,
        x1,
        y1,
        outline=MARQUEE_OUTLINE,
        width=1,
        dash=(4, 3),
        tags=("marquee",),
    )
    for nid in marquee["candidate_ids"]:
        draw_candidate_selection(nid)

def current_marquee_preview():
    for immediate in reversed(immediates):
        if immediate["type"] == "MARQUEE_PREVIEW":
            return immediate
    return None

def draw_callouts():
    canvas = widgets["canvas"]
    canvas.delete("callout")
    if not workspace["callouts"]["active"]:
        return
    entries = callout_entries()
    if not entries:
        return
    width = canvas.winfo_width() or 1200
    height = canvas.winfo_height() or 800
    font = tkfont.nametofont("TkDefaultFont")
    for entry in entries:
        entry["title"] = fit_text_to_px(entry["title"], font, CALLOUT_MAX_TEXT_PX)
        entry["text_w"] = min(font.measure(entry["title"]), CALLOUT_MAX_TEXT_PX)
    widest = max(entry["text_w"] for entry in entries)
    bounds = callout_cluster_screen_bounds(entries)
    cluster_cx = (bounds[0] + bounds[2]) / 2
    cluster_cy = (bounds[1] + bounds[3]) / 2
    side = "right" if cluster_cx < width / 2 else "left"
    text_x = callout_text_x(side, width, widest)
    positions = callout_text_y_positions(entries, height, cluster_cy)
    for i, entry in enumerate(entries):
        text_y = positions[i]
        if side == "right":
            line_start_x = text_x - CALLOUT_PAD
            anchor = "w"
        else:
            line_start_x = text_x + CALLOUT_PAD
            anchor = "e"
        canvas.create_line(
            line_start_x,
            text_y,
            entry["sx"],
            entry["sy"],
            fill=CALLOUT_LINE_FILL,
            width=1,
            tags=("overlay", "callout", "callout_line"),
        )
        canvas.create_text(
            text_x,
            text_y,
            text=entry["title"],
            anchor=anchor,
            fill=CALLOUT_TEXT_FILL,
            font=font,
            tags=("overlay", "callout", "callout_text"),
        )

def callout_entries():
    entries = []
    for nid in workspace["callouts"]["ids"]:
        node = find_node(nid)
        if node:
            sx, sy = world_to_screen(node["x"], node["y"])
            bounds = callout_node_screen_bounds(node)
            entries.append({
                "id": nid,
                "title": node_callout_title(node),
                "sx": sx,
                "sy": sy,
                "bounds": bounds,
            })
    entries.sort(key=lambda entry: entry["sy"])
    return entries

def fit_text_to_px(text, font, max_px):
    if font.measure(text) <= max_px:
        return text
    if max_px <= font.measure("..."):
        return "..."
    trimmed = text
    while trimmed and font.measure(trimmed + "...") > max_px:
        trimmed = trimmed[:-1]
    return trimmed.rstrip() + "..."

def callout_cluster_screen_bounds(entries):
    xs = []
    ys = []
    for entry in entries:
        bounds = entry["bounds"]
        xs.extend([bounds[0], bounds[2]])
        ys.extend([bounds[1], bounds[3]])
    return (min(xs), min(ys), max(xs), max(ys))

def callout_node_screen_bounds(node):
    bounds = node_bounds_world(node)
    if not bounds:
        sx, sy = world_to_screen(node["x"], node["y"])
        return (sx, sy, sx, sy)
    sx0, sy0 = world_to_screen(bounds[0], bounds[1])
    sx1, sy1 = world_to_screen(bounds[2], bounds[3])
    return (min(sx0, sx1), min(sy0, sy1), max(sx0, sx1), max(sy0, sy1))

def callout_text_x(side, canvas_width, widest):
    if side == "right":
        return max(CALLOUT_MARGIN, canvas_width - CALLOUT_MARGIN - widest)
    return CALLOUT_MARGIN + widest

def callout_text_y_positions(entries, canvas_height, cluster_cy):
    count = len(entries)
    row_h = CALLOUT_ROW_H
    available = max(row_h, canvas_height - CALLOUT_MARGIN * 2)
    if count * row_h > available:
        row_h = max(12, available / count)
    total_h = count * row_h
    max_start = max(CALLOUT_MARGIN, canvas_height - CALLOUT_MARGIN - total_h)
    start_y = max(CALLOUT_MARGIN, min(cluster_cy - total_h / 2, max_start))
    positions = []
    for i in range(count):
        positions.append(start_y + i * row_h)
    return positions

def draw_candidate_selection(nid):
    canvas = widgets["canvas"]
    node = projected_node(nid)
    if not node:
        return
    if node["kind"] in ("rect", "text"):
        canvas.create_polygon(
            rect_points(node),
            fill="",
            outline=MARQUEE_CANDIDATE_OUTLINE,
            width=1,
            dash=(2, 2),
            tags=("marquee",),
        )
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
            outline=MARQUEE_CANDIDATE_OUTLINE,
            width=1,
            dash=(2, 2),
            tags=("marquee",),
        )

def draw_node_selection(nid):
    canvas = widgets["canvas"]
    node = projected_node(nid)
    if not node:
        return
    if node["kind"] in ("rect", "text"):
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

def projected_node(nid):
    node = find_node(nid)
    if not node:
        return None
    return projected_node_from_node(node)

def projected_node_from_node(node):
    projected = copy_node(node)
    fields = current_node_preview_fields(node["id"])
    for key in fields:
        projected[key] = fields[key]
    return projected

def current_node_preview_fields(nid):
    fields = {}
    for immediate in immediates:
        if immediate["type"] == "NODE_PREVIEW" and immediate["id"] == nid:
            fields.update(immediate["fields"])
        if immediate["type"] == "NODE_PREVIEW_MAP" and nid in immediate["updates"]:
            fields.update(immediate["updates"][nid])
    return fields
