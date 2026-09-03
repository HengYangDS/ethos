## Why

The full proof currently executes the package-only runtime lifecycle twice: once
through the dedicated `local-install-smoke` gate and again inside the complete
Python test surface. The duplicate architecture-test execution creates a second
acceptance authority, repeats wheel/runtime materialization, and has repeatedly
ended in xdist worker loss even while the dedicated package gate passes.

## What Changes

- Make the existing `local-install-smoke` gate the sole execution owner for the
  proposition that one exact built wheel can complete the package-only
  lifecycle: offline installation, hook/runtime activation, immutable identity
  and manifest readback, runtime relocation and repair, first-lane bootstrap,
  and resumable retirement.
- Keep `unit-architecture` responsible for declarations, dependency boundaries,
  orchestration, and pure contracts; it must not install a wheel or execute a
  second repository lifecycle.
- Classify every existing assertion by semantic owner, migrate each unique
  invariant to that owner, then delete the duplicate executor and its private
  helpers rather than retaining a wrapper, retry, timeout increase, or skip.
- Keep package acceptance evidence bound to the exact HEAD and report the
  lifecycle results from the same receipt that already owns offline
  installation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: require one execution owner for package-only lifecycle acceptance
  and prohibit the complete Python test surface from repeating that lifecycle.

## Impact

The package delivery acceptance owner, its receipt, the delivery pipeline,
focused architecture contracts, the quality specification, and release
governance projection change. No new gate, schema, persistent state, timeout,
compatibility path, adopter carrier, or alternate package lifecycle is added.
