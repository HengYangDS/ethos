## Why

ETHOS currently exposes materially different accepted runtimes under the reused
product version `0.2.0-alpha.2`, while its bundled OpenSpec 1.10.0 trails the
repository-verified stable release. Product version and locked tool supply must
advance together so adopters can compare runtimes and observe the actual
OpenSpec authority without relying on source inspection.

## What Changes

- Advance the single ETHOS product-version authority to `0.2.0-alpha.3` and
  derive publishable manifest projections from it.
- Upgrade the repository-locked official OpenSpec package to exact version
  `1.11.0` across source, lock, build, and runtime projections.
- Advance every other current, repository-declared Python, npm, SBOM, uv CI,
  and hosted Node supply owner to its verified stable release while preserving
  intentional compatibility vectors.
- Close the `0.2.0-alpha.2` changelog section and record the alpha.3 changes
  under Unreleased.
- Preserve exact source commit/tree, wheel digest, and runtime digest as build
  identities distinct from SemVer.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: Product-version projections advance monotonically, current
  supply projections converge, and Node LTS/current compatibility stays exact.
- `repository-governance`: The deterministic official OpenSpec supply advances
  to the repository-locked stable 1.11.0 release.

## Impact

The change updates `VERSION`, Python and npm manifests and locks, the bundled
OpenSpec supply, current tool policies and CI projections, version-facing tests,
current normative documentation, and changelog release sections. It adds no
registry, compatibility carrier, or second version authority.
