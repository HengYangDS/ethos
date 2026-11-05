# Proposal

## Why

0.2.0-beta.2 qualified on 2026-11-05, and governed adopters now run it or 0.2.0-alpha.29. This
lane joins the fixes and features that landed after it:

- `cause-preserving-results`, `archive-test-ownership`: proof results keep each gate's own cause,
  and `unknown` is reported where `block` was;
- `journey-published-predecessor`, `journey-predecessor-set`: the journey upgrades from published
  releases, and from every release adopters still select;
- `dead-carrier-closure`, `peer-address-boundary`, `integration-gap-transport`,
  `quality-fixture-lock`;
- `python-supply-day-old`, `mise-fixed-release-bound`, `mise-execution-ceiling`;
- `release-binary-scan`, `release-binary-scan-refresh`, `adopter-tag-receipts`,
  `mapped-release-retag`, `lease-holder-surface`, `batch-2-integration`.

## What Changes

- `VERSION` and `distributions/npm/package.json` move to `0.2.0-beta.3`.
- The `0.2.0-beta.3` entry is curated from the Unreleased notes. It names:
  - the upgrade paths its journey qualifies, which are 0.2.0-beta.2 and 0.2.0-alpha.29, the
    releases adopters select;
  - the verdict class that commands now report as `unknown`;
  - the journeys this beta does not qualify;
  - the known open defects, none in a blocking class.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A release entry changes no requirement, so `skip_specs: true` applies.

## Impact

`CHANGELOG.md`, `VERSION` and `distributions/npm/package.json`.
