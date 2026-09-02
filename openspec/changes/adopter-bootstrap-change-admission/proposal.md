## Why

Fresh adopter Work Lanes currently receive a bootstrap command that assumes the
checkout lock exposes an `ethos` project entrypoint, even though repository
governance is owned by the selected immutable Git-common package runtime. The
same first-write path reports an uncovered directory when an operator asks to
create the official Change root, then falls through to stale archived intent
instead of identifying the exact metadata artifact that can begin the Change.

## What Changes

- **BREAKING**: make `lane start` return a command through the repository's
  selected immutable package runtime rather than `uv run ... ethos` in the new
  checkout.
- Treat an exact, absent `openspec/changes/<change>` request as bootstrap intent,
  fail closed without granting directory-wide authority, and return the exact
  `.openspec.yaml` prewrite command required before the official OpenSpec create
  command.
- Keep bootstrap admission limited to the official artifact graph and prevent
  archived Change authority from being selected for a new Change root.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: Correct Work Lane runner selection and make the
  initial official Change admission path explicit and non-circular.

## Impact

The change affects Work Lane start projections, current OpenSpec scope
resolution, their public diagnostics, focused unit tests, and the canonical
repository-governance requirements. It does not modify adopters or introduce a
second runtime, intent carrier, or compatibility path.
