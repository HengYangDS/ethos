# Changelog

All notable ETHOS changes are recorded here.

The format follows Keep a Changelog, and commit subjects follow Conventional
Commits.

## [Unreleased]

### Changed

- Repository acceptance, development package builds, and explicit releases now
  have separate identities; accepted source produces a unique PEP 440
  development build instead of silently claiming the release version.
- `proposal/*` is a governed remote review-ref projection; `work/*` remains the
  sole local authoring lane.

### Removed

- Removed the duplicate local `proposal_lane` role and its protected-write
  semantics.
- Removed `channel` and `acceptance_state` from build and runtime manifests.

## [0.2.0-alpha.1] - 2026-08-27

### Added

- The terminal repository trust kernel: canonical Commitment and Attestation
  contracts, deterministic plans, exact Git effects, and post-effect evidence.
- Governed Work Lane and Lease lifecycle, candidate/accepted-root promotion,
  exact object publication, and package-only immutable hook runtimes.
- Repository-native quality, source-budget, evidence, supply-chain, and
  OpenSpec lifecycle gates.

### Changed

- Consolidated the Python implementation into one `ethos` package and removed
  retired compatibility control planes and duplicate lifecycle owners.
- Moved shared mutable runtime state under the Git common directory and made
  generated hooks thin projections over the selected immutable runtime.
- Converged status, plan, proof, mutation, archive, and closeout results on the
  schema-version-2 verdict model.

### Fixed

- Hardened exact-CAS mutation, compensation, ownerless-lane preservation,
  runtime bootstrap, cross-worktree state, and hosted proof execution.

## [0.1.0-alpha.2] - 2026-07-24

### Added

- Release governance files for GitLab visibility: `LICENSE`, `CONTRIBUTING.md`,
  `CHANGELOG.md`, GitLab CI, and GitLab templates.
- Schema validation, gate registry, commit/signature policy, adoption profiles,
  self-evolution ledger, and MCP server descriptor.
- Machine-readable SSH commit signature enforcement for release HEAD checks.
- Secret-scanning gate (gitleaks) and Markdown lint gate (markdownlint-cli2),
  wired into hosted and local CI.

### Changed

- Coverage floor raised to 100% and enforced across
  `coverage.ini`, the test runner, and the coverage policy.
- npm CI jobs install Node from nodejs.org on the cached `python:3.12` image
  instead of pulling the unreachable `node:24` registry image.

### Fixed

- Every CI job auto-retries on infrastructure failures (image-pull timeouts,
  runner faults) while genuine gate breaches still fail immediately.
- Cross-platform coverage: `git_common_dir` and lease-expiry branches are pinned
  so the 100% floor holds on Linux and macOS alike.
- Hardened `coverage.xml` parsing against XXE (defusedxml) and installed taplo
  from a prebuilt binary to avoid a broken aarch64 source build.
- GitLab verification reclones complete history so replay checks resolve pinned
  commits even when a runner workspace was previously shallow.

## [0.1.0-alpha.1] - 2026-06-30

### Added

- Standalone ETHOS product workspace with six package topology.
- Kernel model, action graph, command plane, evidence/provenance, docs registry,
  claims, local state, assistant projections, and product hardening evidence.
