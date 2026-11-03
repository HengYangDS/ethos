# Proposal

## Why

Path-mode prewrite infers a creation for every requested path that is absent from the worktree
(`check_write_paths` and `_check_path` in `src/ethos/adapters/admission/paths.py`). A tracked file
that has been deleted in the worktree therefore reads as a creation, and the paradigm placement
rule, which the repository-paradigm specification applies to creations only, refuses its
retirement with a repair that asks to move it.

- On 11-03 di-effect's Work Lane `serena-activation-ownership` retired the unconsumed
  `.config/tooling/repo/text_boundary_usage.toml`. Prewrite of the deleted path reported
  `repository_paradigm_configuration_group:.config/tooling/repo/text_boundary_usage.toml` with
  the repair "move … under .config/<checks|release>/<owner>/ or a toolchain root".
- Staged admission reads effects from the index and already classifies the path as a deletion.
  Patch mode checks paths without those effects, as path mode does.

## What Changes

- Path mode classifies a requested path that is absent from the worktree as a deletion when the
  index or HEAD tracks it, and as a creation only when neither does.
- The paradigm placement rule and received-path attributes keep applying to creations only.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: prewrite admits the deletion of a tracked path the paradigm rejects.

## Impact

`check_write_paths` and `_check_path` in `src/ethos/adapters/admission/paths.py`, one tracked-path
query in `src/ethos/adapters/repo/git.py`, the prewrite authority tests and the changelog.
