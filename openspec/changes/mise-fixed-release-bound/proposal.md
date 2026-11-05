# Proposal

## Why

mise 2026.11.0 and 2026.11.1 drop, in safe mode, the dependency graph that a lock entry references
([jdx/mise#15363](https://github.com/jdx/mise/issues/15363)). For those versions ETHOS's refusal of
incomplete locked supply names the regression and tells the operator to select a release before
2026.11.0. The condition has no upper bound, because no fixed release existed when it was written.

mise 2026.11.2 fixes the regression. Both fixes, jdx/mise#15392 and jdx/mise#15401, are ancestors of
the `v2026.11.2` tag, which was published on 2026-11-05 at 12:19Z as a stable release. An isolated
recheck of the official macOS arm64 binary passed under `MISE_SAFE=1 MISE_LOCKED=1` on fresh data
for every step: the exact #15363 reproduction, core Python and Go, and wib's eight locked tools.
Without a bound, a refusal under 2026.11.2 or later would blame a fixed regression and send the
operator back to an older mise.

## What Changes

- The regression applies to mise 2026.11.0 and 2026.11.1 only. Under them, the refusal names it and
  points to mise 2026.11.2 or later.
- From 2026.11.2, the refusal names trust or installation, as it does for an earlier mise.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: the locked supply refusal names the regression only for the affected releases.

## Impact

`src/ethos/adapters/toolchain/mise.py` and `tests/unit/adapters/toolchain/test_mise_supply.py`. The
refusal still refuses in every case; only its named cause and next action change.
