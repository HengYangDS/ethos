# Proposal

## Why

The first real `ethos prove --readiness --execute` run on this lane executed 28 readiness gates in
12 minutes, before any host admission, and found two defects that the lane's own Changes had
introduced:

- `dependency-hygiene`: `supply-move-1106` moved filelock, platformdirs and ty in `uv.lock` past
  the floors declared in `pyproject.toml`.
- `module-layout`: the readiness test imports a submodule from its package root, and imports a
  private helper from another test module.

A full proof would have found both only after waiting for its slot.

## What Changes

- `pyproject.toml` raises the floors of filelock, platformdirs and ty to the locked versions.
- The readiness test imports the host module by its full path and builds its own gate graph.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None, so `skip_specs: true` applies.

## Impact

`pyproject.toml`, `uv.lock` and `tests/unit/gates/test_readiness_run.py`.
