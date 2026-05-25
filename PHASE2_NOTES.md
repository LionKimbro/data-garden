# Data Garden CIRA Phase 2 Notes

## Phase 2 Additions

- Added snapshot-based undo/redo through the History Manager section.
- Added semantic `UNDO` and `REDO` events.
- Added `Ctrl+Z` and `Ctrl+Y` bindings.
- Added chord commands `UU` for undo and `RR` for redo.
- Checkpoints capture both compact workspace state and durable world state.
- Redo history is truncated whenever a new committed edit is recorded.
- Continuity state is reset after history jumps while preserving the ordinary raw input bundles.

## Checkpointed Operations

- Create node.
- Delete node.
- Clone node.
- Inspector updates.
- Color changes.
- Camera pan and zoom, compressed into one checkpoint per camera repositioning episode.
- Move and rotate drags, collapsed into one checkpoint at release.
- New project.
- Load project.

## Drag Compromise Removed

Phase 1 emitted `MOVE_NODE` and `ROTATE_NODE` semantic events during drag frames. Phase 2 now emits `PREVIEW_NODE` during drag, which updates the world without recording history, then emits `COMMIT_DRAG` on release to remember the pre-drag checkpoint.

This keeps the program responsive while making one drag undo as one user action.

## Camera History Compression

Middle-button panning and mouse-wheel zooming share one camera episode state. The first camera movement captures the checkpoint, subsequent pan/zoom updates preview the camera without adding history, and the episode commits only after camera input has been quiet for a short debounce window. A pan followed by zoom, or zoom followed by pan, becomes one undoable camera adjustment when they happen as part of the same repositioning burst.

## Remaining Phase 3 Candidates

- Add visible Undo/Redo buttons or menu items.
- Add dirty-state tracking so save prompts can be more precise.
- Decide whether camera-only edits should remain undoable or move into a separate view-history policy.
- Consider replacing whole-world snapshots with deltas if gardens become large.
- Add automated interaction tests around reducer events and history restoration.
