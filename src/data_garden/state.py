# -----------------------
# GLOBAL BUNDLES
# -----------------------

g = {
    "filepath": None,
    "canvas_hot": False,
    "restoring_history": False,
    "base_status": "Ready",
    "hover_status": "",
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
    "drag_selection": {
        "state": "idle",
        "armed": False,
        "node_id": None,
        "was_selected": False,
        "ids": [],
        "start_positions": {},
        "start_checkpoint": None,
        "changed": False,
    },
    "rotate_selection": {
        "state": "idle",
        "ids": [],
        "pivot": None,
        "start_angle": None,
        "originals": {},
        "changed": False,
    },
    "size_selection": {
        "state": "idle",
        "ids": [],
        "handle_name": None,
        "pivot": None,
        "start_dist": None,
        "originals": {},
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
    "marquee_select": {
        "state": "idle",
        "start_sx": None,
        "start_sy": None,
        "current_sx": None,
        "current_sy": None,
        "start_wx": None,
        "start_wy": None,
        "current_wx": None,
        "current_wy": None,
        "candidate_ids": [],
    },
}

continuity = {
    "cycle": 0,
}

workspace = {
    "selection": {
        "ids": [],
        "primary": None,
    },
    "manipulation": {
        "kind": "size",
        "visible": False,
    },
    "hover": {
        "id": None,
    },
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
    "current_revision_guid": "world-rev-000000",
    "revision_serial": 0,
    "revisions": {
        "world-rev-000000": {
            "guid": "world-rev-000000",
            "parent": None,
            "label": "Initial",
            "undo_delta": [],
            "redo_delta": [],
        },
    },
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
