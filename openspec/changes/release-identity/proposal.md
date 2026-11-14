# Proposal

## Why

An accepted release identity names one wheel: the product version, the source commit and tree, and
the digest of the wheel that the accepting host stored
(`src/ethos/repository/release/admission.py`). A release publishes more than that: an archive per
platform, a wheel per native platform, two inventories per archive and a `SHA256SUMS` file that
lists them all. Nothing ties those published bytes to the accepted identity. The release run
attests the archives, wheels and inventories, but not the checksum file itself
(`.config/ci/pipeline.cue`, the step "Attest the release archives and wheels"), so a consumer that
starts from `SHA256SUMS`, as a channel formula will, starts from a file without provenance.

This Change is the first half of row C4 of the release-candidate order
(`openspec/changes/archive/2026-11-07-rc-plan/design.md`, Decision 2, Family 7, and Appendix C.2,
item 4). The approved common-base design splits C4 in two in its decision 4
(`openspec/changes/archive/2026-11-13-common-base-plan/design.md:257-264`): `release-identity`
carries the readers of both identity schemas, the identity binding and the attestation of
`SHA256SUMS`; `release-acceptance` carries the publish refusal and `release accept` one batch
later, so that no adopter takes two breaking steps in one release. The release-candidate gate
requires an attested checksum file (its R8, which DR-0026 records in this batch), and the scope
that the owner approved on 2026-11-14 places this Change in beta.11.

Readers come before the writer, which is the order's rule "expand before contract" (its Appendix
C.1, decision 4): this release reads both payload forms, and no production path writes the new one
until `release-acceptance` gives `materialize_explicit_release` its first caller.

## What Changes

- The release run attests `SHA256SUMS` in the same step as the archives, wheels and inventories,
  before it creates the release.
- An accepted release identity can bind the release's checksum file: the SHA-256 of `SHA256SUMS`
  and the name and digest of every wheel and archive that file lists, beside the version, source
  commit, source tree and accepted wheel that it binds today. Its payload is version 3 of
  `release:accepted-identity`.
- Readers admit version 3 beside versions 1 and 2. A payload recorded without the binding yields
  the identity it recorded, and a later acceptance of the same version, source and wheel with its
  checksum file is admitted beside it.
- Binding refuses before any effect. A published file that the acceptance read and that differs
  from its line, or has none, refuses with `accepted_release_checksum_mismatch:<file name>`; a
  malformed checksum file with `accepted_release_checksums_invalid`; a file that lists no wheel or
  archive with the accepted wheel's digest with `accepted_release_artifacts_invalid`.
- Two acceptances of one version with different checksum files conflict as
  `accepted_version_artifact_conflict`.
- `materialize_explicit_release` takes the checksum file as an optional input and keeps today's
  behavior without it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: MODIFIED requirements `Accepted release identity is immutable`,
  `Public channels consume explicitly accepted release artifacts` and
  `Published release artifacts carry build provenance`.

## Impact

`src/ethos/repository/release/admission.py`, `src/ethos/adapters/repo/runtime/transition.py`,
`.config/ci/pipeline.cue` and its GitHub projection, their tests,
`docs/governance/provenance-and-attestation.md` and a CHANGELOG line. Not Breaking: no recorded
payload changes, and nothing writes version 3 in this release.
