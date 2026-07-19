## Why

The ownerless `work/openspec-scope-recovery-admission-20260715` lane contains
a narrow fail-closed recovery for the one tracked malformed `scope.toml` that
must be edited to restore ordinary material-path coverage. Current accepted
truth lacks that behavior, so neither its preservation package nor a branch
merge can count as absorption.

## What Changes

- Add the smallest current-baseline recovery: admit only one selected tracked,
  malformed Change-local `scope.toml` for repair; do not grant it coverage.
- Add a focused regression that rejects unselected and widened path requests.
- Bind this replay to the source-lane observation and defer every other
  ownerless lane to a separately scoped semantic decision.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=ownerless-openspec-scope-replay;
  reuse=extend; change=modify; facet:lifecycle=authoring,validation,replay;
  facet:surface=cli,openspec,test,evidence; facet:authority=source,test,claim,
  chronicle. A selected tracked malformed scope companion may be repaired only
  for itself; it is not valid material-path coverage until repaired.

## Impact

- `packages/ethos/src/ethos/adapters/openspec/lifecycle/scope.py`
- `tests/unit/lanes/test_lanes_openspec_scope_recovery.py`
- The repository-governance OpenSpec contract and bounded replay evidence.

## Out Of Scope

- Merging, rebasing, cherry-picking, refreshing, landing, or retiring the
  historical source lane.
- Broad ownerless-lane retirement, foreign lease takeover, remote publication,
  hosted execution, or changing official OpenSpec workflow schemas.
