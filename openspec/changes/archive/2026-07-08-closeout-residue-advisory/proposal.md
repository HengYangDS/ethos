# Closeout Residue Advisory

## Why

Multi-agent closeout can leave linked Work Lanes that are already landed, dirty
after landing, unlanded, or diverged. `status` already exposes foreign Work Lane
facts, and `report` already carries advisory signals, but the closeout
disposition needs to be explicit enough for humans and agents to inspect lanes
without guessing.

## What Changes

- Add accepted-root relation and closeout disposition to foreign Work Lane
  status records.
- Derive the disposition from existing Git relation, dirty state, lease, and
  claim binding facts.
- Surface closeout residue as one coarse advisory coordination signal while
  keeping branch-specific details in `foreign_work_lanes[]`.
- Route report advisory next actions to read-only inspection commands.

## Boundaries

No new command, truth store, package, or mutation authority is introduced.
Foreign Work Lanes remain observe-only unless the owner, handoff, or maintainer
break-glass path authorizes mutation.
