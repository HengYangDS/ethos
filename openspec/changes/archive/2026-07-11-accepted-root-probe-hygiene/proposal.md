## Why

An untracked, temporary test probe can leak into an accepted or candidate root
and make it dirty without identifying either its narrow purpose or the safe
next action. The current generic dirty-worktree guidance is truthful but
insufficiently discriminating for people and agents operating concurrent Work
Lanes.

## What Changes

- Classify an untracked Python test file as a temporary probe only when it is
  under `tests/**`, matches `test_*.py`, and declares `TEMP PROBE` in its file
  header.
- Project bounded temporary-probe provenance through workspace status and
  orientation, with a deterministic count, paths, and remediation that asks
  the operator to remove the probe or move it into its owned Work Lane.
- Preserve the existing semantics for all ordinary dirty files; reader views
  will neither delete files nor grant authority over a foreign lane.
- Extend repository-governance requirements, schema validation, and focused
  behavior tests so the distinction remains contractually visible.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=accepted-root-temporary-probe-hygiene;
  reuse=extend; change=modify; facet:lifecycle=validation;
  facet:surface=cli,schema,openspec,evidence;
  facet:authority=source,test,schema,docs,openspec,evidence

## Out Of Scope

- Automatically deleting, relocating, committing, or attributing a temporary
  probe.
- Changing lane ownership, lease, handoff, land, retirement, or foreign-lane
  authority.
- Reclassifying ordinary untracked files, non-Python tests, or files without
  the explicit `TEMP PROBE` header marker.

## Impact

The change affects dirty-worktree provenance, the `orient` reader view, the
workspace-status JSON Schema, repository-governance OpenSpec delta, and their
focused tests. It adds no dependency and no new mutation command.
