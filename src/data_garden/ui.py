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

    canvas = tk.Canvas(paned, bg=CANVAS_BG, highlightthickness=0, cursor="arrow", takefocus=True)
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
    widgets["inspector_apply_widgets"] = []
    widgets["var_id"] = tk.StringVar()
    widgets["var_kind"] = tk.StringVar()
    widgets["var_title"] = tk.StringVar()
    widgets["var_hook"] = tk.StringVar()
    widgets["var_tags"] = tk.StringVar()
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
        widgets["inspector_apply_widgets"].append(entry)
        return entry

    lab("Selected ID"); ent(widgets["var_id"])
    lab("Kind"); ent(widgets["var_kind"])
    lab("Title"); ent(widgets["var_title"])
    lab("Hook"); ent(widgets["var_hook"])
    lab("Tags"); ent(widgets["var_tags"])
    lab("URL"); ent(widgets["var_url"])
    lab("Fill"); ent(widgets["var_fill"])
    build_geometry_row(row)

    i = row["i"]
    row["i"] += 1
    ttk.Label(right, text="Note").grid(row=i, column=0, sticky="nw", padx=8, pady=4)
    text = tk.Text(right, height=10, wrap="word")
    text.grid(row=i, column=1, sticky="nsew", padx=8, pady=4)
    widgets["txt_note"] = text
    widgets["inspector_apply_widgets"].append(text)
    right.rowconfigure(i, weight=1)

    build_inspector_button_row(row)
    bind_inspector_apply_shortcuts()

def build_geometry_row(row):
    right = widgets["right"]
    i = row["i"]
    row["i"] += 1
    ttk.Label(right, text="").grid(row=i, column=0, sticky="w", padx=8, pady=4)
    frame = ttk.Frame(right)
    frame.grid(row=i, column=1, sticky="ew", padx=8)
    widgets["inspector_geometry_row"] = frame

    specs = [
        ("Width:", "var_w"),
        ("Height:", "var_h"),
        ("Angle:", "var_angle"),
    ]
    for col, spec in enumerate(specs):
        label, var_key = spec
        frame.columnconfigure(col * 2 + 1, weight=1)
        ttk.Label(frame, text=label).grid(row=0, column=col * 2, sticky="w", padx=(0 if col == 0 else 6, 3))
        entry = ttk.Entry(frame, textvariable=widgets[var_key], width=9)
        entry.grid(row=0, column=col * 2 + 1, sticky="ew")
        widgets["inspector_apply_widgets"].append(entry)

def build_inspector_button_row(row):
    right = widgets["right"]
    i = row["i"]
    row["i"] += 1
    button_row = ttk.Frame(right)
    button_row.grid(row=i, column=0, columnspan=2, sticky="ew", padx=8, pady=6)
    widgets["inspector_button_row"] = button_row

    buttons = [
        ("btn_apply", "Apply", apply_inspector),
        ("btn_color", "Color", pick_color),
        ("btn_open", "Open", open_link),
        ("btn_clone", "Clone", clone_selected),
        ("btn_delete", "Delete", delete_selected),
    ]
    for col in range(len(buttons)):
        button_row.columnconfigure(col, weight=1)
    for col, spec in enumerate(buttons):
        key, text, fn = spec
        button = ttk.Button(button_row, text=text, command=fn)
        button.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 3, 0 if col == len(buttons) - 1 else 3))
        widgets[key] = button

def bind_inspector_apply_shortcuts():
    for widget in widgets["inspector_apply_widgets"]:
        widget.bind("<Control-Return>", on_inspector_apply_shortcut)
        widget.bind("<Control-KP_Enter>", on_inspector_apply_shortcut)

def on_inspector_apply_shortcut(e):
    if "var_title" in widgets:
        apply_inspector()
    return "break"

# -----------------------
# UI BINDINGS
# -----------------------

def bind_events():
    root = widgets["root"]
    canvas = widgets["canvas"]

    canvas.bind("<Enter>", on_canvas_enter)
    canvas.bind("<Leave>", on_canvas_leave)
    canvas.bind("<Configure>", on_canvas_configure)
    canvas.bind("<Motion>", on_mouse_motion)

    canvas.bind("<Button-1>", on_left_press)
    canvas.bind("<B1-Motion>", on_left_drag)
    canvas.bind("<ButtonRelease-1>", on_left_release)

    canvas.bind("<Button-2>", on_middle_press)
    canvas.bind("<B2-Motion>", on_middle_drag)
    canvas.bind("<ButtonRelease-2>", on_middle_release)

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
