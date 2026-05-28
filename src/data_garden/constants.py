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
CALLOUT_MARGIN = 24
CALLOUT_ROW_H = 20
CALLOUT_PAD = 8
CALLOUT_MAX_TITLE_CHARS = 60
CALLOUT_MAX_TEXT_PX = 260
CALLOUT_TEXT_FILL = "#f8fafc"
CALLOUT_LINE_FILL = "#94a3b8"
TEXT_DEFAULT_FILL = "#f8fafc"
TEXT_DEFAULT_W = 180
TEXT_DEFAULT_H = 40
TEXT_ZOOM_SPAN_FACTOR = 2.0
ZOOM_VISIBILITY_MIN = 0.05
ZOOM_VISIBILITY_MAX = 20.0
MIN_NODE_W = 10
MIN_NODE_H = 10

NODE_KEYS = ("id", "kind", "x", "y", "w", "h", "angle", "fill", "title", "url", "note", "zoom_min", "zoom_max")

CHORD_BITS = {"a": 16, "s": 8, "d": 4, "f": 2, " ": 1}

COMMAND_NAMES = {
    "CR": "Create Rectangle",
    "CC": "Create Circle",
    "CT": "Create Text",
    "PR": "Paste Rectangle",
    "PC": "Paste Circle",
    "PT": "Paste Text",
    "CO": "Color Object",
    "DO": "Delete Object",
    "XO": "Clone Object",
    "XJ": "Clone to JSON",
    "PJ": "Paste from JSON",
    "OL": "Open Link",
    "SF": "Save File",
    "QP": "Quit Program",
    "AA": "Abandon Active",
    "UU": "Undo",
    "RR": "Redo",
}
