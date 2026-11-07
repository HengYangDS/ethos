# Proposal

## Why

The test tree stands at 94,986 of its 95,000 effective-line ceiling, so 14 lines are left. The
converged hardening, store-retention, residue-class, command-forms, peer-identity-records and
history-rebuild-map designs all add tests. The ceiling policy removes accidental complexity first.
`test-budget-margin` showed that the formatter collapses many test constructs onto one line once
their magic trailing commas go. Those commas keep constructs that fit within 100 columns exploded
across several lines.

## What Changes

- Every test module whose constructs fit on one line is formatted once with
  `skip-magic-trailing-comma = true`, and then kept by the repository's own formatter, which
  leaves the collapsed constructs as they are. The change is formatting only: each changed module
  parses to the same syntax tree as before.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None, so `skip_specs: true` applies.

## Impact

- 210 modules under `tests/unit/`, `tests/support/` and `tests/architecture/`. No product code and no
  test behavior changes.
