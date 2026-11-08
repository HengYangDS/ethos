# Proposal

## Why

The keyless marker verifier that `peer-identity-push-check` added refused `cb8e65879` in GitLab's
commit-policy job. Two archived records of `peer-identity-redaction` describe the marker's form by
placeholder label names, and the verifier counted every token that merely ends with the marker's
suffix as a malformed marker, even one with no label at all. A record that documents the marker is
not a broken marker.

## What Changes

- A malformed marker is a run of hexadecimal labels and dots that ends with the marker's suffix
  but is not a marker: a truncated, overlong or uppercase label still refuses as
  `record_marker_malformed`, while a placeholder or the bare suffix in prose does not.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: the keyless verifier's malformed marker is a run of hexadecimal labels.

## Impact

- `src/ethos/repository/paradigm/peer_identity.py` (`malformed_markers`).
- Tests: `tests/unit/repository/test_paradigm_marker_alignment.py` and
  `tests/unit/adapters/repo/commit/test_record_markers.py`.
