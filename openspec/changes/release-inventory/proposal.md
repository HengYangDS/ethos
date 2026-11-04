# Proposal

## Why

A release does not declare what it ships. Its SBOM, from the `release-sbom` owner, describes only
the wheel file: one package with no purls. The runtime archives that adopters install carry
1,749 components on alpha.29's macOS archive, among them uv's Rust crates, the Go modules of CUE,
Vale and shfmt, Node, and the locked Python packages. The design review of 11-04 and its revision
of 11-05 (`build/runtime/work/beta2/grype-design-draft.md`, decision of 11-05 01:05) give the one
existing SBOM owner the archive that the install smoke keeps.

## What Changes

- The `release-sbom` owner (`tools/ci/release_supply_chain.py`, the `supply_chain` session)
  catalogs the runtime archive that the install smoke keeps, instead of the wheel. One Syft run
  writes two inventories:
  - an SPDX 2.3 SBOM, for consumers;
  - a Syft JSON inventory that captures Go symbols, for binary scans.

  Both name the archive's published file name and SHA-256. The run uses the policy's explicit
  Syft configuration and no inherited `SYFT_` setting.

- The owner refuses an inventory that does not name the archive or that lacks an expected
  component. It derives the expected components from their owners:
  - the bundled Go tools' main modules at their declared versions;
  - uv's crates at the locked uv version;
  - Node at its supplied version;
  - every Python distribution that the runtime manifest ships.
- In a proof, the `release-sbom` gate follows `local-install-smoke`. In a release, each platform
  leg runs it after the install smoke and uploads both inventories with its archive.
- Publication admits a host only when its archive, smoke record and both inventories bind to the
  same SHA-256. Each inventory is one regular file under 16 MB.
  - A required host without inventories blocks the release; a Windows host without them is left
    out.
  - Both inventories are published beside the archive, covered by `SHA256SUMS` and by the build
    provenance attestation.
- The wheel-only SBOM goes away.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: a published runtime archive declares what it ships.

## Impact

- `tools/ci/release_supply_chain.py`, `.config/release/release-sbom/policy.toml` and the
  `release-sbom` gate in `system/repository-gates.toml`;
- `tools/ci/delivery/release_assets.py`;
- `.config/ci/pipeline.cue` and its GitHub projection;
- `docs/reference/configuration.md`, the distribution spec and the changelog.
