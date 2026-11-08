# Proposal

## Why

Adopters keep their forges' private identity (host, port and namespace path) in tracked records: on
2026-11-08 DDWG held five such URLs in two decision records and an archived design, and wib one host
and port in an evidence record. An archived record cannot be edited by an ordinary lane, and a
record an adopter keeps must stay verifiable after the literal goes. The archived `rc-plan`
(Appendix F) settles one shared grammar and a redaction verb for this; this Change ships the
grammar, the record roots and the verb, so adopters clear their current trees before the push-time
check (`peer-identity-push-check`) refuses new literals.

## What Changes

- One grammar module, `ethos.repository.paradigm.peer_identity`: the occurrence kinds `url`, `scp`,
  `authority` and bare `host`; the marker `<hex32>.<hex32>.private-peer.invalid`, one HMAC-SHA-256
  over a canonical NUL-joined pre-image; the key reader; keyed replacement of project IDs and ports
  in closed contexts; one boundary definition; and `replacement_spans(line, feed)`.
- The feed, read from local Git state only and never printed: each release peer's remote URLs and
  the `forgeRepository`, `forgeProjectId`, `forgeFormer` and `forgePrivate` keys.
- `record_roots` in the repository profile, directories only; the effective roots are the paradigm's
  immutable roots plus them, with no added immutability.
- `ethos lane redact private-addresses`: a keyless preview listing each occurrence's file, line and
  form, inside or outside the effective roots, and never a value;
  `--apply --key-stdin --authorize --expect-head <oid>`, which writes markers and numbers in the
  effective roots of the working tree under prewrite and the Lease; and
  `--verify --key-stdin --base <rev> --head <rev>`, which re-derives every marker and number and
  records the Attestation `redaction:private-peer`. A redacted file's digest held by a record in the
  same commit follows, and a key of another generation refuses without `--rotate`.
- The content scans accept the peer marker; the bracket marker
  `[redacted:private-network-address:…]`, which no tracked record uses, retires.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: the private-class address requirement names the peer marker, and the
  grammar's kinds, marker, numbers and spans are added.
- `repository-governance`: the repository profile binds `record_roots`.
- `command-plane`: the lane maintainer verbs gain `lane redact private-addresses`.

## Impact

- New `src/ethos/repository/paradigm/peer_identity.py`, `src/ethos/adapters/repo/peer_feed.py`,
  `src/ethos/application/redaction.py` and `src/ethos/surface/cli/lane/redaction.py`;
  `src/ethos/repository/profile.py` (`record_roots` and `effective_record_roots`); the unified patch
  builder moves from `src/ethos/adapters/mutation/source_format.py` to
  `src/ethos/adapters/repo/git_patch.py`, which both verbs use; the paradigm's content scans.
- Tests: grammar vectors per kind, pre-image and key; numbers; contexts and boundaries; the verb's
  preview, apply, verify, digest follow and rotation on fixture repositories, with no value printed.
- Not here (`peer-identity-push-check`): `peer_identity.mode`, the push-time check, the backstop,
  the keyless commit verifier and wib's `[artifacts]` repair.
