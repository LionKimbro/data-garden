# -----------------------
# CONSTANTS / SYMBOLS
# -----------------------

APP_TITLE = "Data Garden - CIRA Phase 7"
CANVAS_BG = "#111215"
GRID_COLOR = "#22252a"
SELECTION_OUTLINE = "#ffd166"
MARQUEE_OUTLINE = "#7dd3fc"
MARQUEE_CANDIDATE_OUTLINE = "#38bdf8"
MANIPULATION_FRAME_OUTLINE = "#fbbf24"
ROTATE_HANDLE_FILL = "#fde68a"
SIZE_HANDLE_FILL = "#bfdbfe"
HANDLE_OUTLINE = "#111215"

NODE_KEYS = ("id", "kind", "x", "y", "w", "h", "angle", "fill", "title", "url", "note")

CHORD_BITS = {"a": 16, "s": 8, "d": 4, "f": 2, " ": 1}

COMMAND_NAMES = {
    "CR": "Create Rectangle",
    "CC": "Create Circle",
    "RO": "Rotate Object",
    "SO": "Size Object",
    "CO": "Color Object",
    "DO": "Delete Object",
    "XO": "Clone Object",
    "OL": "Open Link",
    "AA": "Abandon Active",
    "UU": "Undo",
    "RR": "Redo",
}
