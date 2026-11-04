# Tasks

## 1. Supply

- [x] 1.1 Pin Grype 0.121.1 for Linux and macOS and lock it. Done when `mise lock` records it for
      the four Linux and macOS platforms, and the locked install resolves `grype version` 0.121.1.
- [ ] 1.2 Bind a supply image built from the moved lock. Done when the hosted `supply_image`
      workflow built it from this lane and every GitLab supply job selects its digest.

## 2. Inventory

- [ ] 2.1 Add `tools/ci/delivery/runtime_inventory.py` and the `runtime_inventory` Nox session.
      Done when tests with fixture inventories and a fake Syft show three things: the session
      names the published archive and digest; a missing digest or an empty component list
      refuses; the Go symbol capture is requested.
- [ ] 2.2 Admit the inventories in `release_assets.py`. Done when tests show four things: matching
      inventories are published and summed; a missing inventory refuses; a digest or name
      mismatch refuses; a one-package SBOM refuses.
- [ ] 2.3 Run the session in every `release-platforms` leg and upload its output. Attest each
      host's SPDX with the pinned `actions/attest-sbom`, and add both inventories to the
      provenance subjects. Done when the GitHub projection is regenerated and
      `lane project --check` reports it conforming.

## 3. Scan

- [ ] 3.1 Add `tools/ci/release_binary_scan.py` and the `release_binary_scan` Nox session. Done
      when tests with fixture inventories and fake Grype output show four things: a digest
      mismatch refuses; rows are keyed by archive, package, version and advisory; npm rows are
      marked as audited; a missing host reports as not scanned, and executables without packages
      are named.
- [ ] 3.2 Add the read-only `release-binary-scan` job after `release-publish`, with
      `continue-on-error`. Done when the GitHub projection is regenerated and conforms.
- [ ] 3.3 Accept SBOM input on a real archive. Done when Grype over the session's Syft JSON of the
      alpha.29 macOS archive reproduces the advisory pairs of a direct `dir:` scan with the same
      database.

## 4. Specification and notes

- [ ] 4.1 Add the two `distribution` requirements. Done when strict validation and the cumulative
      archive simulation pass.
- [ ] 4.2 Name the change in the Unreleased notes. Done when the changelog validates.
