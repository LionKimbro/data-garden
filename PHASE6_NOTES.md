# Data Garden CIRA Phase 6 Notes

## Summary

Phase 6 adds conventional left-click dragging of selected objects and selected groups in `datagarden_cira_phase6.py`.

## Removed Movement Paths

- `MO` was completely removed from `COMMAND_NAMES` and command handling.
- Workspace mode `"move_object"` was removed from active code paths.
- The old `move_object` organism was replaced.
- Right-click drag movement was removed.
- Button-3 movement bindings were removed.

## Conventional Drag Selection

- Left press on a selected node arms dragging of the current selection.
- Left press on an unselected node selects that node and arms dragging it.
- Dragging beyond threshold activates movement.
- Releasing without crossing threshold leaves selection as a click-only change.
- Dragging empty canvas remains marquee selection.

## Organism

- `run_drag_selection_organism()` handles object and selected-group movement.
- It uses `idle`, `armed`, and `active` states.

## Judge Resources

- `pointer:left`
- `selection`

These prevent drag selection, marquee selection, rotation, creation, and click selection from competing for the same left-pointer interaction.

## Preview And Commit

- Drag preview uses `PREVIEW_NODES`, which updates node positions without checkpointing.
- On release, the organism emits `COMMIT_DRAG` with the pre-drag checkpoint.
- This preserves the existing one-undo-step-per-drag behavior.

## Undo/Redo

- A completed single-node or group drag creates exactly one undoable movement operation.
- Undo restores all moved nodes together.
- Redo reapplies the group movement together.
- Selection-only changes remain non-undoable.

## Temporary Compromises

- Drag previews still mutate the world during the drag. This matches prior phases and keeps projection simple.
- A later phase can move drag previews into immediates or projection-local preview state.

## Suggested Phase 7

- Add a visual group frame around selected objects.
- Add projected manipulation handles.
- Add a visible rotation handle.
- Defer actual group rotation until a later phase if needed.
