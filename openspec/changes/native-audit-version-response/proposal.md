# Proposal

## Why

The dependency audit rejects the JSON string returned by the current native npm registry view.
Its test transport wraps strings in arrays, hiding that mismatch and blocking valid observations.

## What Changes

- Read a native version string or a single version string in an array at the existing audit owner.
- Exercise the actual response shape without adapting it in the test transport.
- Preserve strict handling of incomplete observations and findings with an available upgrade.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This repairs implementation of the existing quality requirements; `skip_specs: true` applies.

## Impact

The dependency-audit reader and its regression tests change. No dependencies, locks, risk
dispositions, release metadata, runtime bindings or publication contracts change.
