## Why

The complete 35-gate proof at `26405d4d8` passed in 2,171.66 seconds with two
workers. Pytest consumed 1,925.09 seconds. One representative release case made
1,610 subprocess calls and rebuilt source identity twenty times. The user
requires complete verification within 600 seconds, not merely cached verdicts.

## What Changes

- Attribute elapsed time, repeated work and native startup at existing owners.
- Remove measured duplicate observation and compilation without reusing stale
  authority or silently narrowing source inputs.
- Reduce cold full-suite work before considering cross-run evidence reuse.
- Preserve all behavioral obligations, native effects and the coverage floor.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: measured complete-proof throughput with unchanged assurance.

## Impact

Existing Git/source/runtime observation and gate execution owners, shared native
test fixtures, their regression tests and the canonical terminal plan.
No new lane, authority, daemon, adopter mutation or mandatory caching service.
Release promotion is archived but not yet accepted; its remaining proof and
delivery obligations stay open while this measured bottleneck is addressed.
