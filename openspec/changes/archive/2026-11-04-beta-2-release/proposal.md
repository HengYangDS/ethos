# Proposal

## Why

After 0.2.0-beta.1, which publishes alpha.30's code, the next prerelease on the 0.2.0 line is a
beta, because Semantic Versioning orders every beta after every alpha. This lane carries four
Changes that adopters need before the release candidate:

- `host-admission`: one host-wide queue for heavy local work, and a load limit that `host.toml`
  declares;
- `ref-retirement-routes`: absorbed-ref retirement previews that agree with the prepared hook, and
  a route to retire a legacy role ref that duplicates its successor;
- `windows-source-retry`: generated Windows jobs retry their source checkout;
- `skill-package-routing`: the Skill portfolio names a package that no record routes.

## What Changes

- `VERSION` and `distributions/npm/package.json` move to `0.2.0-beta.2`.
- The `0.2.0-beta.2` entry is curated from the four Changes. It names the journeys this beta does
  not qualify and the known open defects, none of which is in a blocking class.
- The tag is cut only after beta.1's tag exists and this head's hosted verification has passed on
  every supported platform. The release run's journey legs are this beta's adopter-journey
  evidence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A release entry changes no requirement, so `skip_specs: true` applies.

## Impact

`CHANGELOG.md`, `VERSION` and `distributions/npm/package.json`.
