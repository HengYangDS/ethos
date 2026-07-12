## Context

The exercise ran on isolated copies.  Raw command envelopes and protected-file
digests are host-local diagnostics, not repository truth.  ETHOS records
revisions, outcomes, preservation assertion, and bundle identity without
copying adopter content.

## Goals / Non-Goals

**Goals:** record exact revisions, all profile outcomes, preservation, bundle
hash, and the local-only non-authorizing boundary.

**Non-Goals:** re-run the exercise; validate semantics, provider configuration,
or hosted CI; add an adopter, account, credential, service, key, or
`yheng-agent-ethos` prerequisite; or track host paths, raw envelopes, protected
bytes, or remote state.

## Decisions

### Digest-bound claim, not semantic attestation

`digest_only` binds the Chronicle to one local packet.  It is not independent
review, semantic proof, or authority.

### Summarize outcomes; retain raw material locally

The Chronicle records apply state, comparison and false-negative counts,
preservation count, matched state, and bundle hash.  The packet stays
host-local; a second repository evidence root is not created.

### Provider labels are profile selectors

`github` and `gitlab` name local profiles, not hosted access, execution, or
authority.  The same kernel and boundary apply to every profile.

## Risks / rollback

A digest cannot validate meaning; any semantic claim needs its own reviewed
receipt.  If raw material disappears, this remains a historical hash, not fresh
evidence.  Revert only this carrier, claim, and Chronicle: no adopter, runtime,
provider, or remote state changed.
