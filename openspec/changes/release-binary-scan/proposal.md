# Proposal

## Why

The release audit covers the Python lock and the npm lock. It cannot see the vulnerable code
compiled into the binaries the runtime ships:

- the rustls inside uv;
- the Go standard library and modules inside CUE, Vale and shfmt;
- Node itself.

Those findings were found by hand after release, on 10-28 and 11-03. The owner decided on 11-03
that a binary-aware scan comes after alpha.29, and the design review of 11-04 settled the shape
(`build/runtime/work/beta2/grype-design-draft.md`). The release SBOM cannot serve as the input: it
describes only the wheel file, one package with no purls. A Syft catalog of an installed runtime
lists 1,749 packages, including uv's rustls and three Go standard library versions.

## What Changes

- Mise pins Grype 0.121.1 for Linux and macOS, the hosts that run the scan. Grype publishes no
  Windows arm64 build.
- A new Nox session, `release_binary_scan`, runs in the hosted release run after publication,
  outside every landing gate. It does these things:
  - downloads each published runtime archive;
  - verifies the archive against the release's `SHA256SUMS`;
  - catalogs the archive once with the pinned Syft;
  - scans that catalog with the pinned Grype.
- It writes one report:
  - Grype's version, and the database build time, URL and checksum;
  - each archive's digest;
  - one row per (archive, package, version, advisory) with severity and fix state;
  - npm rows marked as already audited, binaries without metadata listed by name, and a missing
    host reported as not scanned.
- The job reports and does not block (`continue-on-error`), and runs outside the job that holds
  release write permissions.
- Enforcement comes in a later Change: a binary subject in the dependency acceptance policy.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: a release run reports the binary-level vulnerabilities of what it shipped.

## Impact

- `.config/mise/config.toml` and `mise.lock`, and with them a rebound supply image;
- `.config/ci/pipeline.cue` and its GitHub projection;
- `noxfile.py` and a new `tools/ci/release_binary_scan.py` with tests;
- the distribution spec and the changelog.
