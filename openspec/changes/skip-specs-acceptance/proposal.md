## Why

OpenSpec accepts completed `skip_specs: true` Changes whose intent is carried by
official proposal, design, tasks, and metadata rather than requirement deltas.
ETHOS currently rejects the same official projection as
`openspec_acceptance_missing`, so valid release, tooling, and documentation
Changes cannot pass the public prove/archive lifecycle without inventing a fake
spec delta or adding a parallel carrier.

## What Changes

- Compile deterministic, non-empty acceptance from official OpenSpec artifacts
  when a completed Change explicitly declares `skip_specs: true` and has no
  requirement deltas.
- Keep undeclared or incomplete zero-delta Changes fail-closed.
- Preserve the existing requirement/scenario compilation for Changes that carry
  deltas.
- Prove the same acceptance before archive and through the existing attested
  archive transition after archive.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: Official spec-free OpenSpec Changes participate in
  the same transient Commitment and proof lifecycle without fake requirements.

## Impact

The change is limited to the existing OpenSpec Commitment compiler, its focused
tests, and lifecycle regressions. It adds no tracked carrier, schema, registry,
compatibility path, or adopter-specific behavior.
