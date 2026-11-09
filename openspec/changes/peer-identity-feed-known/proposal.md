# Proposal

## Why

`required` promises that a push cannot carry a protected peer's identity to another peer, but every
local reader of the feed treats a feed it cannot know as a clean one. A clone that holds no
protected peer's remote, such as a fresh clone of the public peer, has an empty feed: push admission
passes it, the redaction preview counts zero, the apply reports `unchanged` and the verify records a
`redaction:private-peer` Attestation over a range it could not judge. The archived design of
`peer-identity-push-check` promised to refuse a protected peer whose remote cannot be read, as
`peer_identity_feed_unreadable:<remote>`; neither its specification nor its code does. A remote
marked `forgePrivate` outside the publication declaration is never fed at all.

## What Changes

- The feed reader feeds every protected declared peer and every other remote marked `forgePrivate`,
  and names what it cannot know: an invalid publication declaration's own gaps, else
  `peer_identity_feed_unreadable:<remote>` for each declared peer whose remote has no configured
  URL, else `peer_identity_feed_empty` when it feeds nothing.
- Under `required`, push admission refuses with those gaps before it reads any advertisement, and
  its decision reason for every peer identity gap becomes `peer_identity_refused`.
- With those gaps, `ethos lane redact private-addresses` answers `unknown` in every mode before it
  validates or uses a key: the preview still lists what it reads, the apply writes nothing and the
  verify records nothing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: push admission under `required` refuses a feed the clone cannot know.
- `command-plane`: the redaction verb answers `unknown` without a known feed.

## Impact

- `src/ethos/adapters/repo/peer_feed.py`, `src/ethos/adapters/admission/peer_identity_push.py`,
  `src/ethos/adapters/admission/publication.py` and `src/ethos/application/redaction.py`;
  `src/ethos/application/peer_identity.py` follows the reader's new return.
- Tests: `tests/unit/adapters/repo/test_peer_feed.py`,
  `tests/unit/adapters/admission/test_peer_identity_push.py` and
  `tests/unit/cli/test_lane_redaction.py`, whose fixtures gain the second declared peer's remote.
- The redaction and push-check paragraphs of `docs/reference/operational-roots.md`, and the two
  Unreleased CHANGELOG entries that added the verb and the push check. Neither is released, so no
  Fixed entry is due.
- A clone that pushes under `required` must configure a remote for every declared peer. The owner's
  root and its lanes share one configuration that does; push admission runs only in the local
  pre-push hook and `ethos publish`, so no hosted job changes. `status` keeps its rules and now
  also sees an undeclared remote marked `forgePrivate` as a protected peer.
