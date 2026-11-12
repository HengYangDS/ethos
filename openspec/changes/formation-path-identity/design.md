# Design

## Context

See the [proposal](proposal.md). `formation_plan` in `src/ethos/adapters/repo/starter/formation.py`
resolves the requested parent, names the target inside it, and hashes the canonical `root`, the
candidate worktree path and `source_inputs`, which hold `requested_root` beside the parent's device
and inode. `form_repository` in `src/ethos/application/adoption.py` builds the apply continuation
with `--root` set to the canonical target. Before it writes, `_publish` resolves the requested
parent again and refuses `formation_parent_changed` unless it is the same directory, by path, device
and inode.

## Goals / Non-Goals

Goals:

- A continuation run verbatim after a preview applies the plan that the preview showed.
- A parent retargeted between preview and apply still refuses.

Non-Goals:

- Any change to which destinations formation admits, or to the checks that `_publish` repeats.
- A detail for other digest mismatches.

## Decisions

1. `requested_root` leaves `source_inputs`, so it is neither hashed nor reported. The digest keeps
   the canonical root, the candidate worktree path and the parent's device and inode, which name the
   destination without its spelling.
2. A test previews once through a linked parent and once through the canonical path that the first
   preview reports, and requires one digest. It fails before the change. The existing retarget test
   keeps proving that a retargeted parent refuses.

## Risks / Trade-offs

- A caller can no longer see in the preview which spelling it used. The preview reports the
  canonical root, which is the destination that apply writes.
