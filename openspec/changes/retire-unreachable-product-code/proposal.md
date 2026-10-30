# Proposal

## Why

`per-file-ceiling-parameters` brings every ETHOS Python file to 500 effective lines by splitting
modules. Each new module costs its own imports, so the splits raise `python_product` above its
70,000-line terminal budget, and `adapters/repo/git.py` stays above 500.

A reachability scan of `src/ethos` found product functions that no product code, tool or
declaration calls. Only their own tests do. Such code costs budget and reading time, and its tests
prove behavior that no consumer depends on. Removing it pays for the splits without loosening any
check.

## What Changes

- Remove nine functions that nothing but their own tests calls, with the helpers and protocols only
  they use, and `evaluate_cel_value`, which only two of them called. One of them,
  `exact_rename_target`, brings `adapters/repo/git.py` under 500.
- Remove seven functions whose behavior a live function already owns. Their tests move to that
  live function, or are dropped where it is already tested for the same case.
- Fold `remove_untracked_tree`, a one-line wrapper, into the helper it called.
- Keep `release_policy_report` and `materialize_explicit_release`. Specifications still require
  their behavior even though no live path runs them; whether to wire them or amend those
  specifications is a separate decision.
- Keep `terminal_schema_documents`. The schema test uses it to keep
  `system/schemas/kernel/*.schema.json` equal to the models.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No requirement depends on the removed functions; `skip_specs: true` applies.

## Impact

- Product modules under `src/ethos/adapters/`, `src/ethos/contracts/` and
  `src/ethos/repository/` lose the functions listed in the design, and their tests change with
  them.
- `python_product` returns within its terminal budget with room for the next fix.
- Out of scope: the two specification gaps above. The design records them and their next action.
