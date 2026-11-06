# Proposal

## Why

0.2.0-beta.3 shipped without Windows runtimes. Its Windows legs failed their inventory check, so
DDWG, the one governed adopter that installs ETHOS on Windows, stays on 0.2.0-beta.2. The lane
`20261105-release-path` landed the fixes:

- `release-node-declaration`;
- `release-declared-legs`;
- `release-step-coverage`;
- `release-node-digest-typing`;
- `secrets-supply-seam-test`.

This lane adds `release-identity-check` and `audit-reset-resilience`. beta.4 publishes them, with
Windows runtimes restored.

## What Changes

- `VERSION` and `distributions/npm/package.json` move to `0.2.0-beta.4`.
- The `0.2.0-beta.4` entry is curated from the landed Changes. It names:
  - the upgrade paths that its journey qualifies: 0.2.0-beta.3, 0.2.0-beta.2 and 0.2.0-alpha.29;
  - the journeys that this beta does not qualify;
  - the known open defects, none in a blocking class.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A release entry changes no requirement, so `skip_specs: true` applies.

## Impact

`CHANGELOG.md`, `VERSION` and `distributions/npm/package.json`.
