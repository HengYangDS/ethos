# Proposal

## Why

The hosted release journey for v0.2.0-beta.6 (run 42331951579) failed on linux-x64 and macos-arm64
with `package_retained_publication_repair_failed`. The product was not the cause.

- The successor's `lane repair-paradigm` on the legacy retained fixture, a `task/`-prefix adopter,
  removes the two retired publication fields.
- It also normalizes the six default-valued `branch_roles` fields that the fixture declares in
  `.ethos/workspace.toml`.
- The harness required the repaired gaps to equal the two retired gaps exactly.
- Its unit test replaced the CLI with a fake that returned only those two gaps. So the real repair
  first ran against the real fixture at tag time.

## What Changes

- The retained publication repair requires both retired publication gaps to be repaired. It admits
  any other repaired gap only from the branch-roles obligation, and it records the complete
  repaired list in its report.
- Its unit test runs the real `lane repair-paradigm` on the real retained fixture, so the repaired
  set is the product's own before any tag.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The journey harness is qualification tooling, so `skip_specs: true` applies.

## Impact

`tools/ci/delivery/acceptance/brownfield.py` and
`tests/unit/ci/delivery/runtime/test_retained_upgrade.py`.
