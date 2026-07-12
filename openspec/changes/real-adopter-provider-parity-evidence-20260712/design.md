## Context

The real-adopter exercise was deliberately run on temporary isolated copies.
Those command envelopes and protected-file digests are useful diagnostic
material, but their paths and full contents are host-local rather than tracked
repository truth.  The repository needs a compact promotion record that is
precise about revision, profile result, integrity assertion, and raw-bundle
identity without copying either the adopter or its content into ETHOS.

## Goals / Non-Goals

**Goals:**

- Record the exact product and isolated-adopter revisions observed.
- Record all three requested profile outcomes and the preservation assertion.
- Bind the observation to the SHA-256 of its host-local raw bundle.
- Make the local-only and non-authorizing boundary explicit.

**Non-Goals:**

- Re-run adoption or shadow parity as part of this evidence-only change.
- Validate the adopter's governance semantics, provider configuration, or
  hosted CI.
- Add a named adopter, a provider account, a credential, a daemon, a key, or
  `yheng-agent-ethos` as a prerequisite.
- Promote host paths, raw command envelopes, protected source bytes, or remote
  state into tracked evidence.

## Decisions

### Digest-bound claim, not semantic attestation

The claim uses `digest_only`.  It establishes that the Chronicle is bound to a
specific local observation packet.  It does not turn an overlay result into an
independent review, semantic-correctness, or authority claim.

### Profile outcomes are summarized, not re-materialized

The Chronicle records only the outcome facts required to audit the exercise:
apply state, command-comparison count, false-negative count, preservation
count, and matched state.  The raw packet is identified by SHA-256 and remains
host-local so it can be inspected under local access controls without making a
second evidence root in the repository.

### Provider labels remain profile selectors

`github` and `gitlab` in this record identify local adoption profiles.  They do
not assert hosted-provider access, status, execution, or authority.  The same
kernel and claim boundary apply to every listed profile.

## Risks / Trade-offs

- **A digest cannot validate semantic meaning** — this is declared through
  `digest_only`; a future semantic claim must carry its own independent review
  receipt and verification evidence.
- **A raw bundle may become unavailable on the host** — the tracked record
  remains an honest historical pointer by hash and must not invent a replacement
  packet or claim freshness.
- **Profile success may be overread as adoption completion** — the Chronicle
  states the excluded lifecycle and remote boundaries explicitly.

## Rollback

Revert only this carrier, claim, and Chronicle.  No adopter, product runtime,
provider projection, or remote state needs rollback because none is changed.
