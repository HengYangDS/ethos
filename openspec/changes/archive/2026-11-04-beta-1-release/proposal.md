# Proposal

## Why

The distribution specification selects a beta by evidence, not by age. Its release head must
pass hosted verification on every supported platform. Its code must pass the declared adopter
journey from published artifacts on macOS and Linux. No known defect may corrupt an installation,
block a landing or admit a wrong proof. `0.2.0-alpha.30` closes the last known defect of that
kind: a locked npm that Mise reported as missing resolved silently to Node's bundled npm. Its
release run exercises the journey from its published artifacts. The owner asked on 2026-11-03 for
a beta as soon as possible.

## What Changes

- `VERSION` and `distributions/npm/package.json` move to `0.2.0-beta.1`. No product code changes,
  so beta.1 ships the code that alpha.30 published.
- The `0.2.0-beta.1` entry names:
  - the criteria and where their evidence lives;
  - the journeys this beta does not qualify;
  - the known open defects, none of which is in a blocking class.
- The tag is cut only after alpha.30's release run has passed both journey legs and this head's
  hosted verification has passed on every supported platform.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A release entry changes no requirement, so `skip_specs: true` applies.

## Impact

`CHANGELOG.md`, `VERSION` and `distributions/npm/package.json`.
