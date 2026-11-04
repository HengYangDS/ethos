# Proposal

## Why

The release audit covers the Python lock and the npm lock. It cannot see the vulnerable code
compiled into the binaries the runtime ships:

- the rustls inside uv;
- the Go standard library and modules inside CUE, Vale and shfmt;
- Node itself.

Those findings were made by hand after release, on 10-28 and 11-03. The release also does not
declare what it ships. Its SBOM describes only the wheel file: one package, with no purls. Both
gaps have one cause: no release names the binaries inside its runtime archives. The design review
of 11-04 and its revision of 11-05 (`build/runtime/work/beta2/grype-design-draft.md`) settle one
inventory per shipped archive. It is produced at build, published and attested, and the scan reads
it.

## What Changes

- Each release platform leg catalogs its own runtime archive with the pinned Syft 1.56.0 after
  the install smoke has built it. The catalog captures Go function symbols. Each leg writes:
  - an SPDX 2.3 SBOM;
  - a Syft JSON inventory.

  Both name the archive's published file name and its SHA-256.

- Publication admits each inventory only when it names the admitted archive's digest and lists
  components. An admitted archive without both inventories fails assembly.
  - `SHA256SUMS` covers the inventories, and they are published as release assets.
  - `actions/attest-sbom` binds each SPDX SBOM to its archive.
  - The build provenance attestation covers both inventories.
- A read-only `release-binary-scan` job follows publication, with `continue-on-error`. It
  downloads only the inventories and `SHA256SUMS`, checks their digests, and runs the pinned
  Grype 0.121.1 on each Syft JSON. Its report names:
  - the scanner and its database;
  - each archive's digest;
  - one row per archive, package, version and advisory;
  - npm rows, marked as already audited;
  - executables that no package identifies, listed by name;
  - a missing host, reported as not scanned.
- Mise pins Grype 0.121.1 for Linux and macOS, the hosts that scan. Grype publishes no Windows arm64
  build.
- Enforcement comes in a later Change: a binary subject in the dependency acceptance policy.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`:
  - a published runtime archive comes with attested inventories that name its digest and its
    components;
  - a release run reports the binary-level advisories of those inventories without blocking.

## Impact

- `.config/mise/config.toml` and `mise.lock`, and with them a rebound supply image;
- `.config/ci/pipeline.cue` and its GitHub projection;
- `noxfile.py` sessions;
- `tools/ci/delivery/release_assets.py`;
- new `tools/ci/delivery/runtime_inventory.py` and `tools/ci/release_binary_scan.py`, with tests;
- the distribution spec and the changelog.
