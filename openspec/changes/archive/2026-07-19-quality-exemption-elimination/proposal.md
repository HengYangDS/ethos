## Why

ETHOS still accepts a green Python-quality result through Ruff global and
per-file ignores, a ratchet baseline, and source-level suppressions. That
contradicts the declared terminal law: an applicable rule must report zero
findings on every governed asset.

## What Changes

- Remove the first independently provable Ruff exception slice: replace the
  implicit local calendar with UTC and delete the `DTZ011` ignore and ratchet
  record.
- Route type checks through the checkout-local runtime bootstrap so an
  unmaterialized lane neither resolves another environment nor emits ambient
  virtual-environment noise.
- Record the terminal zero-exception architecture as the successor target; it
  remains unimplemented until its full finding inventory is refactored.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: replace ratchet-based Python-quality acceptance with direct,
  zero-finding enforcement for every governed Python asset;
  subject=quality:terminal-exception-contract; reuse=extend; change=modify;
  facet:lifecycle=validation; facet:surface=ci; facet:authority=source.

## Impact

The change affects the UTC/DTZ011 policy slice, checkout-bound type runtime,
quality evidence, OpenSpec, and regression tests. It does not remove the
remaining exception carriers, introduce another quality command plane, or
change foreign Work Lanes.

## Out of Scope

- Removing remaining global/path Ruff ignores, source suppressions, the ratchet
  file, or its runner. Those require independently verified refactor waves.
- Changing source-budget, remote-publication, hosted-CI, or foreign Work Lane
  state.
