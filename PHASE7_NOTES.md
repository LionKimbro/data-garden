# Data Garden CIRA Phase 7 Notes

## Summary

Phase 7 replaces full-world undo/redo snapshots with World Model revision GUIDs and reversible delta notes.

## Snapshot Policy

History checkpoints no longer contain complete world snapshots or node lists. A checkpoint now has this shape:

```python
{
    "workspace": {...},
    "world_revision_guid": "world-rev-000001",
    "label": "Update",
}
```

Workspace snapshots still store editor state such as mode, awaiting-click command, and camera.

## World Revision Packets

World revisions live in `world["revisions"]` and have this shape:

```python
{
    "guid": "world-rev-000001",
    "parent": "world-rev-000000",
    "label": "Update",
    "undo_delta": [...],
    "redo_delta": [...],
}
```

`world["current_revision_guid"]` names the current durable world revision.

## Delta Notes

Supported note operations:

- `create_node`
- `delete_node`
- `restore_node`
- `update_node`
- `replace_world`

Normal edits use small per-node notes. New/Open use a fresh root revision policy instead of being stored in ordinary undo/redo history.

## Recording Forward And Reverse Notes

World effect handlers capture the old node fields or nodes before mutation, apply the mutation, then call `record_world_revision(label, undo_delta, redo_delta)`.

Preview effects do not record revisions.

## Undo / Redo Navigation

Undo/redo checkpoints point to target world revision GUIDs. `goto_world_revision()` walks from the current revision to the target revision, applies `undo_delta` notes while moving backward, and applies `redo_delta` notes while moving forward.

Redo branching is handled by clearing the redo stack when a new checkpoint is remembered. Old revision packets may remain in `world["revisions"]`.

## Save / Load Policy

Project JSON remains compatible:

```json
{
  "version": 1,
  "nodes": [],
  "camera": {},
  "next_id": 1
}
```

Undo/redo history and world revisions are not saved into project files. File Open and New clear undo/redo history and establish a fresh root world revision.

## Selection Policy

Selection-only changes are still not undoable. History snapshots do not store selection. After a world revision jump, the live selection is reconciled against the restored world.

## Preview Compromise

Drag and rotation previews still mutate `world["nodes"]` without recording a revision. On release, one final revision is recorded from explicit before/after delta notes. A later phase should move preview state out of the World Model and into continuity/projection preview state.

## Known Limitations

- Revision packets are retained even after redo branching; no branch garbage collection exists yet.
- Delta notes are simple dictionaries and do not yet include compression or coalescing.
- New/Open are not undoable in this phase; they reset revision history.

## Suggested Phase 8

- Add a visual group frame around selected objects.
- Add projected manipulation handles.
- Add a visible rotation handle.
- Use tokenizers/organisms/Judge for handle hit-testing.
- Defer full group rotation until a later phase if needed.
