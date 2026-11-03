# Proposal

## Why

A decision record can commit a Change to a ruling that the Change never takes up. DR-0013, written
on 2026-10-17, names the `repository-paradigm` Change, which moved the release mirror's policy
field. That Change archived on 10-18 without the historical reader the record requires, the gap then
blocked the proposal-retirement journey, and `publication-history-repair` implemented the rule only
on 10-22. Nothing connects a record to the Change it names, so archive cannot notice that the Change
never took the decision up. The end-state design, revision 6.9, approved on 2026-11-01, routes this
check as `decision-citation` in its first phase.

## What Changes

- Archive readiness reads the decision records of the exact tree that the archive preview or the
  proof judges. When a record names the active Change in inline code, the Change must cite the
  record, by its `DR-####` identity or its file name, in one of its artifacts; otherwise archive
  readiness reports `openspec_decision_uncited:<change>:<identity>`, which blocks the archive
  preview and the proof that selects the Change.
- The Docs Registry guide states the rule beside the decision record contract.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: a Change archives only after it cites every decision record that names
  it.

## Impact

`src/ethos/adapters/openspec/archive_readiness.py`, its tests in
`tests/unit/openspec/test_archive_readiness.py`, `docs/governance/docs-registry.md` and
`CHANGELOG.md`. Every governed repository that keeps decision records gets the check.
