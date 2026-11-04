# Tasks

## 1. Supply

- [x] 1.1 Pin Grype 0.121.1 for Linux and macOS and lock it. Done when `mise lock` records it for
      the four Linux and macOS platforms, and the locked install resolves `grype version` 0.121.1.
- [ ] 1.2 Bind a supply image built from the moved lock. Done when the hosted `supply_image`
      workflow built it from this lane and every GitLab supply job selects its digest.

## 2. Scan

- [ ] 2.1 Add `tools/ci/release_binary_scan.py` and the `release_binary_scan` Nox session. Done when
      tests with fixture archives and a fake scanner show four things: the archive digest is
      checked against `SHA256SUMS`; rows are keyed by archive, package, version and advisory; npm
      rows are marked as audited; a missing archive reports as not scanned.
- [ ] 2.2 Add the `release-binary-scan` job to the release run in `.config/ci/pipeline.cue`, with
      read permissions and `continue-on-error`, after `release-publish`. Done when the GitHub
      projection is regenerated and `lane project --check` reports it conforming.

## 3. Specification and notes

- [ ] 3.1 Add the `distribution` requirement. Done when strict validation and the cumulative
      archive simulation pass.
- [ ] 3.2 Name the change in the Unreleased notes. Done when the changelog validates.
