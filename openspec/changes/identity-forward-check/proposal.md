# Proposal

## Why

The owner directed on 2026-10-31 that wrappers, aliases and renames without independent semantics
be removed and kept out by mechanism. `pass-through-removal` removed eight product pass-throughs and
made module layout refuse renaming aliases and imports through a module that does not define the
name, but it kept one identity forward, `openspec_base_command` in
`src/ethos/adapters/openspec/cli.py`, as a test seam, and nothing refuses a new one. The end-state
design, revision 6.9, routes this check as `identity-forward-check` in its first phase.

## What Changes

- Module layout refuses an identity forward in ETHOS's product code: a module-level, undecorated
  function whose one statement returns a call to a function that the module defines or imports,
  passing every parameter unchanged and nothing else.
- `openspec_base_command` becomes the owner of the locked command resolution that it forwarded to,
  and `run_json_batch` calls it.
- `rules/module-layout.md` names the refusal beside the facade rules.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The quality specification's "Semantic And Physical Isomorphism" already makes facades block
proof; this Change implements the check for their function form.

## Impact

`src/ethos/repository/policy/layout/facades.py` and `report.py`,
`src/ethos/adapters/openspec/cli.py`, tests in
`tests/unit/policy/test_layout_facade_public_branches.py`, `rules/module-layout.md` and
`CHANGELOG.md`. The module-layout gate is ETHOS's own, so no governed repository is affected.
