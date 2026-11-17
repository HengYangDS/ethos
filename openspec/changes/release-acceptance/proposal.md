# Proposal

## Why

Two functions that implement stated requirements have no production caller.
`release_policy_report` (`src/ethos/repository/release/configuration.py`) computes the product's
release policy gaps, and no command reads it. `materialize_explicit_release`
(`src/ethos/adapters/repo/runtime/transition.py`) admits, stores and attests an accepted release
identity, and no release path runs it. A release is therefore tagged and published without its
policy being read, and no accepted identity is recorded for it. The archived
`2026-10-30-retire-unreachable-product-code` design kept both functions for a Change that wires
them.

This Change is the second half of row C4 of the release-candidate order
(`openspec/changes/archive/2026-11-07-rc-plan/design.md`, Decision 2, Family 7, and Appendix C.2,
item 4). The archived `rc-scope-plan` design places it in the batch of 2026-11-28, and DR-0029
keeps that batch. Its first half landed in 0.2.0-beta.11 as the archived Change
`2026-11-14-release-identity`: the accepted identity can bind the attested checksum file, and
readers admit that form. The reader shipped one release before this writer, which is the order's
rule "expand before contract".

## What Changes

- In the repository that declares the ETHOS product profile, `ethos publish` refuses a release tag
  while the release policy report holds a required gap. The result names the gap and a next step.
- A governed repository's publication does not change. Its report-first form is the draft Change
  `release-ref-policy-report`.
- A new operation, `ethos release accept --checksums <SHA256SUMS> [--apply]`, accepts on the
  releasing host the release that the invoked installation is. It previews by default. With
  `--apply` it stores the release's wheel and records the accepted identity once, bound to the
  checksum file. A second run changes nothing.
- The operation refuses before any effect, with a registered repair, when the invoking `ethos` is
  no installed release build, when its version is older or newer than the version the accepted
  branch commits, when that version has no tag, and when the installed wheel was not built from the
  tagged commit.
- The release guide states the acceptance step and how a bad global release is undone: reinstall
  the predecessor.

Breaking, for the product repository alone: after the first applied acceptance, an engine older
than 0.2.0-beta.11 refuses the accepted identity set with `accepted_release_attestation_invalid`.
The reader shipped in 0.2.0-beta.11, so that repository's runtime rolls back no further than that
release.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: MODIFIED requirements `Accepted release identity is immutable` and
  `Public channels consume explicitly accepted release artifacts`, and one ADDED requirement,
  `The releasing host accepts the release that it installed`, which holds the host's
  acceptance and its six scenarios as a behavior of its own.

## Impact

`src/ethos/application/land/release_acceptance.py` and `src/ethos/contracts/operations/release.py`
(new); the catalog and its implementation table; the console's runtime selection; the publication
inspection; the release configuration; the release transition and the installed wheel reader; six
rows of the gap registry; their tests; `docs/reference/operational-roots.md`,
`docs/reference/command-plane.md`, `docs/guides/release-and-publication.md` and a CHANGELOG entry.
