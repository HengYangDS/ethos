# Changelog

All notable ETHOS changes are recorded here.

The format follows Keep a Changelog, and commit subjects follow Conventional
Commits.

## Unreleased

### Added

- Release governance files for GitLab visibility: `LICENSE`, `CONTRIBUTING.md`,
  `CHANGELOG.md`, GitLab CI, and GitLab templates.
- Schema validation, gate registry, commit/signature policy, adoption profiles,
  self-evolution ledger, and MCP server descriptor.
- Machine-readable SSH commit signature enforcement for release HEAD checks.
- Secret-scanning gate (gitleaks) and Markdown lint gate (markdownlint-cli2),
  wired into hosted and local CI.

### Changed

- Coverage floor ratcheted to 100% (no exemptions), enforced across
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

## 0.1.0a1 - 2026-06-30

### Added

- Standalone ETHOS product workspace with six package topology.
- Kernel model, action graph, command plane, evidence/provenance, docs registry,
  claims, local state, assistant projections, and product hardening evidence.
