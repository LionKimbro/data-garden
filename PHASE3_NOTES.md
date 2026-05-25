# Data Garden CIRA Phase 3 Notes

## What Changed

- Created `datagarden_cira_phase3.py` as the Phase 3 runnable prototype.
- Replaced loose callback interaction behavior with an explicit CIRA continuity cycle:
  `RAW -> tokenizers -> organisms -> Judge -> semantic events -> reducer -> effects -> projection`.
- Tkinter pointer/key callbacks now update RAW facts and run the app cycle.
- Added explicit DERIVED facts, tokenizer state, a Judge resource table, and organism state machines.
- Undo/redo and New/Open now reset continuity systems rather than replaying or restoring them.

## Tokenizers Added

- `tokenize_pointer()`
- `tokenize_buttons()`
- `tokenize_keyboard()`
- `tokenize_target()`
- `tokenize_drag()`
- `tokenize_wheel()`

## Organisms Added

- `run_chord_organism()`
- `run_awaiting_target_organism()`
- `run_create_object_organism()`
- `run_click_selection_organism()`
- `run_move_object_organism()`
- `run_rotate_object_organism()`
- `run_camera_pan_organism()`
- `run_camera_zoom_organism()`

## Judge Resources

- `keyboard:chord`
- `pointer:left`
- `pointer:middle`
- `pointer:right`
- `camera`
- `selection`
- `node:<id>`

## Preserved Behavior

- Rectangle and circle creation through CR/CC chords.
- Click selection and clearing selection by clicking empty canvas.
- Move mode, right-drag move, rotate mode, color, delete, clone, and open-link commands.
- Inspector editing and apply behavior.
- JSON save/load compatibility with `version`, `nodes`, `camera`, and `next_id`.
- Atomic save.
- Ctrl+Z/Ctrl+Y and UU/RR undo/redo.
- One undo checkpoint per node drag.
- Camera pan/zoom history compression into one camera repositioning episode.

## Temporary Compromises

- Drag and rotate previews still use `PREVIEW_NODE`, which temporarily mutates the world during the drag and commits one checkpoint on release. This preserves Phase 2 behavior, but a later phase can move previews into immediates/projection-private state.
- Chord finalization is still timer-driven by `after()`. The timer callback emits semantic command events and pumps the app, which is practical for tkinter but not a pure frame-loop runtime yet.
- Ctrl+Z/Ctrl+Y bindings still go directly to undo/redo helpers rather than entering through RAW keyboard tokenization.

## Known Bugs Or Uncertain Areas

- Camera wheel input during an active middle-button pan is blocked by the Judge because the pan organism owns `camera`; this keeps ownership simple and predictable.
- The target tokenizer uses current canvas items for hit testing, so projection must be refreshed before hit testing reflects recent world changes.
- Selection remains a single id, not a selection set.

## Suggested Phase 4

- Convert selection from a single id to a selection list/set in workspace.
- Add marquee selection as a new organism.
- After selection sets exist, add group dragging as a separate organism.
- Move drag previews out of world mutation and into projection/immediates.
