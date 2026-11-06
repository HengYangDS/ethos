# Proposal

## Why

Each of the last two release runs failed at a step that runs only when a release is published:

- Release run 42099003242 failed all its legs on `materialize_tool(ROOT, "syft")` with
  `mise_unavailable`. The run's binary scan later failed the same way for Grype.
- Release run 42117725176 failed both Windows legs on an inventory component that only a Windows
  archive lacks.

The common cause is how tools/ci gets native tools. `materialize_tool` falls back to the mise on
PATH, and a GitHub job stages mise in the tool cache but never puts it on PATH. So a session works on
the operator's host and fails in any job whose staging list misses its tool. The release's inventory
step also never runs on Windows before a tag. And `tools/ci/toolchain/native.py` keeps its own copy
of the native tool set, a copy that lacks Grype.

## What Changes

- tools/ci materializes every native tool through the repository's own digest-bound mise, with one
  helper, `supply_tool`, at the four call sites: Gitleaks, Syft, Grype and the Node supply.
  - A job's staging list now only prefetches, and the release runtime job no longer stages Syft.
  - An architecture test refuses any other direct call to `materialize_tool` in tools/ci. It
    replaces the Syft-only staging test.
- `native.py` takes its tool choices from the native supply registry.
- Each host-conformance leg whose runner and Python match a declared release leg catalogs the runtime
  archive that its install smoke kept, with `nox -s supply_chain`, on every hosted commit run.
  - Proposals cover linux-x64, macos-arm64 and windows-x64; dev adds windows-arm64.
  - GitLab's proof already catalogs the Linux ARM64 archive through the `release-sbom` gate.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: release platforms catalog their archives on every hosted commit run.
- `quality`: a repository session obtains native tools through the repository's own mise.

## Impact

- `tools/ci/toolchain/native.py`, `tools/ci/release_supply_chain.py`,
  `tools/ci/release_binary_scan.py` and `tools/ci/sessions.py`.
- `.config/ci/pipeline.cue`, its projection `.github/workflows/ci.yml`, and `tests/architecture/ci/`.
- Host-conformance legs on a release leg's Python take about 15 s longer on Linux and macOS and
  about 45 s longer on Windows.
- Out of scope:
  - a per-commit binary scan;
  - the pre-tag release rehearsal of release-mode builds, publication, the scan and the journey,
    which is its own Change.
