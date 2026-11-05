# Proposal

## Why

The batch-2 proof `b2p1` at `f26eb9e4e` stopped at `repository-hygiene`:
`tools/ci/release_binary_scan.py:69: forbidden quality suppression: type-ignore`. The report
builder typed `report` as `dict[str, object]` and then indexed `report["archives"]`, which a type
checker rejects, so the line suppressed the error. Repository hygiene forbids that suppression.

## What Changes

- The report builder keeps its archives in a typed local mapping and puts that mapping in the
  report, so no suppression is needed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Typing an internal mapping changes no requirement, so `skip_specs: true` applies.

## Impact

`tools/ci/release_binary_scan.py`.
