# Proposal

## Why

The release run publishes ETHOS's platform archives and wheels with a `SHA256SUMS` file and no
provenance, so nobody can check that a published file came from ETHOS's own workflow at the signed
tag. Mise's GitHub backend verifies GitHub artifact attestations whenever a release asset carries
them, which is the verification that the approved end-state design's `github-pin` relies on
(section 3, item 2: "the release workflow produces none today, so `github-pin` adds the attestation
step to the release run"). Attesting first, in its own Change, lets the next release carry the
attestations that the pin then verifies.

## What Changes

- The CI model's release publication job attests every published archive and wheel with
  `actions/attest-build-provenance` before it creates the release, and gains the `id-token` and
  `attestations` write permissions that the attestation needs.
- The GitHub projection is regenerated, and the release publication test covers the step, its
  subjects, its order and the permissions.
- `docs/governance/provenance-and-attestation.md` states what the release provenance establishes
  and how it differs from ETHOS's proof Attestations; `CHANGELOG.md` records the change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: published release artifacts carry build provenance.

## Impact

`.config/ci/pipeline.cue`, the generated `.github/workflows/ci.yml`, one test, one governance
document and `CHANGELOG.md`. The attestations first appear with the next release; no product code
or adopter configuration changes.
