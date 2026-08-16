# Change: Carry terminal-v1 prestate into accepted closeout

## Why

Candidate integration already carries the exact terminal-v1 repository identity
when promoting a v2 Commitment. Accepted closeout did not carry the same
prestate coordinates, so its dry-run passed but its Git effect was rejected as
`git_effect_repository_identity_mismatch`.

## What Changes

- Resolve the exact terminal-v1 repository carrier at the accepted HEAD.
- Reuse the existing repository-bootstrap admission fields in accepted closeout.
- Keep malformed, missing, foreign, or byte-drifted carriers fail-closed.

## Impact

- Affected code: accepted closeout plan compilation and its focused regression.
- No new authority, state, compatibility reader, or generic identity bypass.
