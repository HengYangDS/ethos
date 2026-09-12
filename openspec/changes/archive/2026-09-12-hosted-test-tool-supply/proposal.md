## Why

GitLab verify job 37430 at accepted source e34d894 failed five native scanner
regressions because its own environment did not provide gitleaks. Success of a
separate secrets job cannot supply another job's process. Missing prerequisites
must fail before the expensive test suite, not after twenty minutes.

## What Changes

- Prepare the existing pinned scanner through its native installer in the
  shared hosted-proof entrypoint, alongside source-budget supply.
- Verify preparation failure stops proof, removes stale output, and retains the
  original diagnostic; exercise both prerequisite owners and successful supply.
- Preserve real scanner regressions, coverage requirements, concurrency and
  exact-source hosted result semantics.
- Close demonstrated gaps in native Git index recovery and compensation
  regressions. The Python 3.14 full run reproduces GitHub's 94.986% coverage;
  retain the 95% floor and test real failure behavior rather than suppress code.

## Capabilities

### Modified Capabilities

- `quality`: hosted verification prepares all native test prerequisites before
  the test gate executes, independently of other jobs or ambient tools.

## Impact

`tools/ci/scripts/run-head-bound-proof.sh`,
`tests/unit/ci/test_hosted_verification.py`,
`tests/unit/mutation/test_git_effect_operations.py`, the quality specification and the
existing terminal plan. Both Forge projections invoke the shared entrypoint.

## Non-Goals

No new installer, tool registry, compatibility layer, skip, relaxed timeout,
concurrency increase or adopter mutation. Proposal review ingress remains the
next independent bounded repair in the same authorized Work Lane.
