# Proposal

## Why

`supply-currency` derived the Mise floor in the projection test's bootstrap-version fault from
`.config/mise/config.toml` instead of naming it. The added constant put
`tests/architecture/test_ci_provider_projections.py` at 501 effective lines, one above the per-file
ceiling of 500, and the lane proof stopped at the repository paradigm gate.

## What Changes

- The fault names the moved floor, `2026.10.24`, again, and the module returns to 500 effective
  lines.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The test keeps its assertion, so `skip_specs: true` applies.

## Impact

`tests/architecture/test_ci_provider_projections.py` only.
