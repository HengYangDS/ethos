# Proposal

## Why

The release audit covers the Python lock and the npm lock. It cannot see the vulnerable code
compiled into the binaries the runtime ships:

- the rustls inside uv;
- the Go standard library and modules inside CUE, Vale and shfmt;
- Node itself.

Those findings were made by hand after release, on 10-28 and 11-03. Change `release-inventory`
makes every release publish a symbol-capturing Syft JSON inventory per runtime archive. This
Change scans those inventories after publication, as decided on 11-05 01:05
(`build/runtime/work/beta2/grype-design-draft.md`).

## What Changes

- Mise pins Grype 0.121.1 for Linux and macOS, the hosts that scan. Grype publishes no Windows arm64
  build. The product's native supply resolves the platform-scoped declaration.
- A read-only `release-binary-scan` job follows publication, with `continue-on-error`. It
  downloads only the Syft inventories and `SHA256SUMS`, checks their digests and subjects, and runs
  the pinned Grype on each. Its report names:
  - the scanner and its database;
  - each archive's digest;
  - one row per archive, package, version and advisory;
  - npm rows, marked as already audited only when their shipped lock equals the audited lock;
  - executables that no package identifies, by name;
  - a host whose inventory is missing, as not scanned.
- Enforcement comes in a later Change: a binary subject in the dependency acceptance policy.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: a release run reports the binary-level advisories of what it shipped.

## Impact

- `.config/mise/config.toml` and `mise.lock`, and with them a rebound supply image;
- the native supply's backend table;
- `.config/ci/pipeline.cue` and its GitHub projection;
- a new `tools/ci/release_binary_scan.py` and its Nox session, with tests;
- the distribution spec and the changelog.
