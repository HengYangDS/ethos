## Why

ETHOS still accepts a green Python-quality result through Ruff global and
per-file ignores, a ratchet baseline, and source-level suppressions. That
contradicts the declared terminal law: an applicable rule must report zero
findings on every governed asset.

## What Changes

- **BREAKING**: make the selected Ruff rule set an unconditional repository-wide
  quality law; delete global ignores, per-file ignores, the ignored-rule
  ratchet, and its runner.
- Reject retained Python source suppressions and removed ratchet carriers through
  product contracts and regression tests.
- Keep one Ruff policy and one owner script; CLI, hooks, CI, proof, and profiles
  remain projections of those owners.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: replace ratchet-based Python-quality acceptance with direct,
  zero-finding enforcement for every governed Python asset;
  subject=quality:terminal-exception-contract; reuse=extend; change=modify;
  facet:lifecycle=validation; facet:surface=ci; facet:authority=source.

## Impact

The change affects Ruff policy and runner surfaces, quality gate/tool
registries, quality documentation, OpenSpec, and regression tests. It does not
introduce another quality command plane, a compatibility layer, or changes to
foreign Work Lanes.

## Out of Scope

- Treating this initial DTZ011 deletion as evidence that all remaining Ruff
  exception carriers have been eliminated.
- Changing source-budget, remote-publication, hosted-CI, or foreign Work Lane
  state.
