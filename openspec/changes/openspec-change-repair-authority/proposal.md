## Why

An owned Work Lane can reach a deadlock when strict OpenSpec validation names
an error in the selected active Change itself. ETHOS currently summarizes that
failure as `openspec_validation_failed:change:<change>` but its only validation
repair scope recognizes canonical specifications, so the exact official delta
file identified by OpenSpec cannot be corrected through public prewrite.

## What Changes

- Extend the existing validation-repair scope to consume the selected Change's
  structured official `validate --json` issue paths for strict-blocking
  `ERROR` and `WARNING` issues, and admit only the unique exact existing
  official artifacts those paths identify. Informational issues never grant
  mutation authority.
- Keep canonical-spec repair and active-Change repair under one ephemeral
  validation-repair owner; do not add a repair token, carrier, registry, state
  table, compatibility path, or directory-wide permission.
- Preserve each official output's lexical repository path, require the exact
  target to be a non-symlink regular file, reject malformed, absolute,
  traversing, missing, ambiguous, unrelated-Change, and mixed requested paths,
  and require strict validation to be re-observed after the edit.
- Preserve Work Lane, Lease, actor, runtime, editor-root, and tracked-path
  admission unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: Official validation repair covers an exact active
  Change artifact named by the current structured validator result, rather
  than only an invalid canonical specification.

## Impact

The existing OpenSpec artifact-path projection, lifecycle scope adapter,
current authority resolver import, repository-governance specification, and
focused admission tests change. Commitment, Lease, OpenSpec artifact, command,
and persistence schemas do not change.
