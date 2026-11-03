# Proposal

## Why

GitHub issue 20 asks that a repository's own formatter configuration be an optional increment on
the settings ETHOS ships, and that an incompatible increment be refused before any mutation.
`paradigm-single-source` delivered the shared baseline in `v0.2.0-alpha.26`, and the issue's
closure waits on one observable journey: the public `ethos lane format` fix, run without
`--check` against a conflicting increment, refusing before it writes any selected file. Two tests
cover the conflict (`test_conflicting_native_increment_refuses_all_postimages` and
`test_conflicting_python_formatter_increment_cannot_replace_shared_policy` in
`tests/unit/adapters/gates/test_source_format.py`), and both run only `--check`. The renderer
prepares every postimage before the fix writes (`_format_source` in
`src/ethos/adapters/mutation/source_format.py`), but no test runs that fix against a conflict.

## What Changes

- The two conflict tests run both the check and the authorized fix (`--apply --authorize
  --expect-head`). Each mode reports `native_formatter_policy_conflict` and blocks, and the
  selected files, the increment and the index keep their bytes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The `repository-governance` requirement "Applicable shared quality is supplied by the
product" already requires that local configuration cannot cause source mutation and that native
policy errors block without source writes; only tests change, so `skip_specs: true` applies.

## Impact

`tests/unit/adapters/gates/test_source_format.py`. No product, lock or adopter change.
