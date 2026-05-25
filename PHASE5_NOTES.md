# Data Garden CIRCA Phase 5 Notes

## Summary

Phase 5 adds rectangular marquee selection to `datagarden_circa_phase5.py` using the Phase 3 CIRA continuity architecture and the Phase 4 plural selection model.

## Marquee Behavior

- Press left mouse on empty canvas to arm marquee selection.
- Drag beyond the existing threshold to activate the marquee.
- Release to replace the current selection with candidate nodes.
- Release before the threshold clears selection, preserving the old empty-click behavior.
- Marquee selection is not undoable.

## Tokenizers

- `tokenize_drag()` now exposes drag start/current screen and world coordinates.
- Existing pointer, button, target, keyboard, and wheel tokenizers are unchanged in role.

## Organism Added

- `run_marquee_select_organism()` with `idle`, `armed`, and `active` states.
- The organism stores preview rectangle coordinates and candidate ids locally in `organisms["marquee_select"]`.

## Judge Resources

- Marquee uses `pointer:left` and `selection-preview`.
- This prevents click selection from also firing while marquee owns the left pointer.

## Candidate Computation

- Candidates are selected by world-space axis-aligned rectangle intersection.
- Circles use their world bounding boxes.
- Rectangles use transformed rotated corners, then axis-aligned bounds.
- Helpers added:
  - `node_bounds_world()`
  - `rect_points_world()`
  - `rect_bounds_from_points()`
  - `rects_intersect()`
  - `selection_candidates_in_world_rect()`

## Projection

- `draw_marquee()` draws a dashed marquee rectangle.
- Candidate nodes receive temporary dashed outlines.
- Preview state is read from the marquee organism rather than committed to workspace selection during drag.

## History Policy

- `SET_SELECTION` does not checkpoint.
- Marquee selection does not checkpoint.
- History snapshots no longer store selection.
- Undo/redo restores world/camera/mode state, then reconciles the current live selection against the restored world.
- Invalid selected ids are dropped; if primary is gone, another selected id is chosen or primary is cleared.

## Remaining Compromises

- Marquee preview reads organism-local state directly from Projection instead of flowing through `immediates`.
- Candidate selection uses bounding-box intersection rather than exact rotated polygon intersection.
- Additive/toggle marquee selection is intentionally not implemented.

## Suggested Phase 6

- Add conventional group dragging:
  - click selected object and drag moves all selected objects
  - click unselected object selects it
  - drag selected group as one undoable operation
  - preserve CIRA organism/Judge architecture
