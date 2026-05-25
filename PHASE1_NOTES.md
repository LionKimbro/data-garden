# Data Garden CIRA Phase 1 Notes

## Preserved Behaviors

- Tkinter Canvas map editor with dark background and grid.
- Rectangle and circle node creation through two-letter chord commands.
- Node selection by clicking.
- Moving and rotating nodes.
- Fill color changes through color picker.
- Clone, delete, and open-link commands.
- Inspector fields for title, url, fill, width, height, angle, and note.
- JSON save/load with `version`, `nodes`, `camera`, and `next_id`.
- Atomic JSON writes.
- Chording over `a/s/d/f/space` with the original bit mapping.
- Camera pan with middle mouse and mouse-wheel zoom centered around the pointer.
- Coordinate transforms use the realized projection camera.

## CIRA Subsystem Locations

- Constants and symbols: `CONSTANTS / SYMBOLS`.
- Global state bundles: `GLOBAL BUNDLES`.
- Tkinter construction: `UI BUILD`.
- Tkinter event wiring: `UI BINDINGS`.
- Raw input, chord capture, mouse episodes, pan, zoom, move, and rotate interpretation: `CONTINUITY: RAW / CHORDS / MOUSE`.
- Hit testing and coordinate transforms: `CONTINUITY: PICKING / COORDINATES`.
- Semantic event queue entry point: `DISCRETE: EVENTS`.
- Semantic state transitions and command interpretation: `DISCRETE: REDUCER`.
- Effect handling for world mutation, dialogs, browser opening, status, and inspector refresh: `EFFECT ROUTING`.
- Durable node data and `next_id`: `WORLD MODEL`.
- Canvas items, grid, selected outline, and realized camera: `PROJECTION`.
- Inspector read/apply behavior: `INSPECTOR`.
- Serialization, normalization, and atomic writes: `FILE OPS`.
- Undo/redo placeholder: `HISTORY PLACEHOLDER`.
- Queue draining and reducer/effect routing: `RUNTIME`.

## Intentional Temporary Compromises

- Move and rotate dragging emit `MOVE_NODE` and `ROTATE_NODE` semantic events during drag frames so the UI remains live. Phase 2 should collapse a drag into one undoable semantic operation on release.
- Some GUI effects, such as delete confirmation and color picking, are routed as effects that may emit follow-up semantic events.
- Projection redraws the whole grid and all nodes after semantic changes. This is simple and clear for Phase 1.

## Phase 2 Undo/Redo Work

- Add checkpoint packets that capture `workspace` semantic state and a world revision.
- Snapshot or delta-record world mutations from reducer effects.
- Convert drag episodes into one checkpointed command at release.
- Truncate redo on new committed edits.
- Add `UNDO` and `REDO` semantic events and runtime state-jump handling.
- Reset continuity state after any time-travel jump while preserving valid raw input facts.

## Bugs Or Ambiguities Found In `datagarden4.py`

- The original stores `canvas_item` directly on node dictionaries during rendering, so saved JSON can leak tkinter canvas item ids.
- `cmd_delete_object` and `cmd_clone_object` are defined twice.
- `execute_cmd` refers to `cmd` in an unknown-command branch even though the argument is named `code`.
- The original command map names `LO` as Link Object, but the implementation table uses `OL` for opening links.
- `NO`, `TO`, and some edit-oriented commands appear in comments or maps but are not fully implemented.
