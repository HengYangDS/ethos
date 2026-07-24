## Why

The accepted repository contains one duplicate Markdown blank line that makes
the hosted quality workflow stop before repository proof. The same owner script
reproduces the defect locally, so the correction must be landed as repository
truth rather than treated as runner-specific noise.

## What Changes

- Remove exactly one redundant blank line from the affected closeout plan.
- Bind the corrective Work Lane to a dedicated claim and dated evidence.
- Preserve the current Markdown policy, document meaning, and CI topology.

## Capabilities

### New Capabilities

None. This change introduces no product capability.

### Modified Capabilities

- `quality`: Clarify the existing documentation quality profile with the
  already-enforced Markdown owner-script failure boundary.

## Impact

The change affects one plan document, the existing quality specification, and
their OpenSpec and evidence carriers. No API, package, dependency, runtime
behavior, quality threshold, foreign Work Lane, or remote publication contract
changes.
