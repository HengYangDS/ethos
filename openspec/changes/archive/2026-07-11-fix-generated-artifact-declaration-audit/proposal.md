## Why

The generated-artifact entrypoint audit scans every non-comment line in `pyproject.toml` as though it were an executable producer. Adopter cleanup paths, ignore globs, and exclusion lists therefore create blocking gaps even though they only prevent or remove generated state.

## What Changes

- Classify executable `pyproject.toml` task commands separately from declarative configuration values.
- Continue blocking real producer commands that route caches or artifacts to denied homes.
- Add adopter-shaped regression tests covering cleanup paths, ignore globs, and actual Pixi task producers.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: Generated-artifact entrypoint auditing distinguishes declarative path mentions from executable producers.

## Impact

Affected surfaces are the generated-artifact policy parser and focused unit tests. The topology contract, denied path set, and adopter configuration remain unchanged.
