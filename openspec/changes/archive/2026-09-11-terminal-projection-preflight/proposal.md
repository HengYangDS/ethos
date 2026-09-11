## Why

Official archive updated two canonical specification inputs but left terminal
architecture source bindings stale. The architecture quick gate did not call
the official exporter, so a known source-readiness defect consumed another full
test run before being reported.

## What Changes

- Reconcile the selected graph with the archived source meaning and refresh only
  reviewed bindings; retain the full product scope and target/current boundary.
- Connect the existing immutable-tree exporter to the existing architecture
  gate and require that gate before heavy tests through the sole registry.
- Exercise stale, missing and valid committed sources through the quick gate;
  retain independent native rendering checks and exact export identity.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This tooling repair implements the existing quality requirements for
source-faithful terminal export and inexpensive failure before heavy verification.
No new product semantics or fake specification delta is required.

## Impact

The terminal graph, existing architecture gate, registry, focused regressions
and sole terminal plan. Routing stays with repository and quality governance.
The archived artifact-origin Change remains history. No new Work Lane, adopter
write, renderer change, dependency, runtime authority or parallel validation owner.
