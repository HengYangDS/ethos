## Why

An owned, clean Work Lane with a valid Lease cannot create its first official
OpenSpec Change through the public write path. After the official CLI creates
`.openspec.yaml`, prewrite requires a complete Commitment before it permits the
proposal, design, specs, or tasks that are needed to compile that Commitment.
This is a circular admission dependency at the sole tracked-intent boundary.

## What Changes

- Admit creation and completion of exactly one official active Change root when
  no transient Commitment can yet be compiled.
- Restrict bootstrap admission to paths declared by the official OpenSpec
  artifact graph under that exact active Change root.
- Keep every product, test, documentation, configuration, and unrelated Change
  path blocked until the official Change is complete and ordinary Commitment
  attribution applies.
- Reuse current Work Lane authority and the existing `CurrentScope` resolution;
  add no command, carrier, schema, registry, compatibility path, or durable
  bootstrap state.
- Remove the stale command-plane requirement that still advertises the deleted
  `ethos lane start-change` lifecycle.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: Tracked-write admission gains a bounded official
  Change bootstrap state before transient Commitment compilation.
- `command-plane`: The public next action names the official OpenSpec artifact
  command instead of the deleted `lane start-change` surface.

## Impact

The change affects current OpenSpec resolution, prewrite material attribution,
command-plane diagnostics, and focused lifecycle regressions. It does not alter
Lease persistence, product-path scope, runtime activation, publication, or
adopter-specific policy.
