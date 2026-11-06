# Proposal

## Why

An invalid repository profile reports only `repository_profile_invalid:.ethos/profile.toml`. An
agent migrating an adopter's old schema-1 profile cannot tell from the result what to change. On
2026-11-06 alphasim's 178-line profile carried 20 keys that the current profile model rejects, and
the result named none of them.

## What Changes

- A failing profile validation keeps each problem as a value-free code: its kind and key path, such
  as `extra_forbidden:schema_version` or `value_error:roots.rules`.
- The invalid-profile result carries the problems in `data.profile_problems`, at most 20, with
  their count, and its next action points at them. The stable gap is unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: the invalid-profile result names its problems.

## Impact

- `src/ethos/repository/profile.py`, `src/ethos/domain/execution.py`, `src/ethos/cli.py`,
  `src/ethos/surface/cli/output.py`, and the land and publish operations that return the result.
