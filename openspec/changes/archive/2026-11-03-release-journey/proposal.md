# Proposal

## Why

A beta needs the declared adopter journey to pass from the published artifacts on macOS and Linux
("Prereleases advance on declared journey evidence" in the distribution specification): a cold
install, host-store pinning, hook binding, a full proof and status, an upgrade from the previous
release with its rollback, and uninstall. No hosted job runs any of these steps on a published
release.

- The package acceptance that hosted runs execute installs a locally built wheel, and it runs the
  upgrade and rollback only when given a predecessor runtime, which no hosted job passes, so its
  receipts record `retained_state_upgrade: not_qualified`.
- The adopter path of `v0.2.0-alpha.27` and `v0.2.0-alpha.28` was accepted by a local operator
  script on macOS only, against a local checkout of another repository. Linux has no such evidence.

## What Changes

- A Nox session `release_journey` qualifies one published prerelease on the adopter journey from
  its release assets alone: it verifies the platform archive against the release's checksums and
  build attestation, installs it through Mise as adopters do, and runs the journey's steps in
  fixture adopters on fresh host stores. The previous release is the one whose changelog entry
  follows the prerelease's.
- A GitHub job `release-journey` runs that session on `ubuntu-latest` and `macos-latest` after a
  release run publishes its prerelease, and a dispatch input `journey_tag` runs it alone for an
  already published prerelease. Each leg uploads its receipt and stage events.
- The Mise installation of a declared ETHOS tool moves to its own module, which the distribution
  acceptance and the journey share.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: a hosted journey qualifies each published prerelease on macOS and Linux.

## Impact

`tools/ci/delivery/acceptance/journey.py` and `tools/ci/delivery/mise_tool.py` (new),
`tools/ci/delivery/distribution.py`, `tools/ci/delivery/acceptance/adopter.py`,
`tools/ci/sessions.py`, `.config/ci/pipeline.cue` and the generated `.github/workflows/ci.yml`,
their tests, the release guide and the changelog.
