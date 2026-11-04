# Proposal

## Why

The full proof of `559e837a8` failed `unit-architecture` only on the coverage floor: 94.99%
against the required 95%, with all 7,861 tests passing. The refusal paths that
`locked-supply-completeness` and `locked-supply-per-tool` added are untested:

- an unreadable or malformed `mise ls` report;
- a Mise version that cannot be read;
- a lock that is not TOML;
- a 2026.11 Mise whose missing tool has no graph-referenced lock entry.

The inventory memo's refusals of an unusable directory at save time are untested too.

## What Changes

- Tests cover each of those paths. No product code changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Only tests change, so `skip_specs: true` applies.

## Impact

`tests/unit/adapters/toolchain/test_mise_supply.py` and
`tests/unit/adapters/repo/runtime/test_inventory_memo.py`.
