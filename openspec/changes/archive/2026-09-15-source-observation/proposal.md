## Why

Hosted proof of accepted `e7eb7c4c` failed after a closeout case reached its
300-second deadline and one runtime fixture exceeded a ten-second smoke timeout.
A current one-case profile observes 20 complete workspace reads and 27 source
identity compilations; source compilation has no deadline and reads moving HEAD
coordinates independently. Reduce this read amplification without weakening
fresh admission or changing test budgets.

## What Changes

- Observe the exact ref or worktree topology a closeout projection needs instead
  of recursively collecting unrelated runtime, Lease and dirty-state facts.
- Pin the source commit, reject HEAD movement during source compilation, and
  bound the complete native Git observation with a retained failure cause.
- Keep the native isolated index, complete non-ignored overlay and fresh effect
  checks; do not introduce a metadata-only identity shortcut or persistent cache.
- Verify the historical closeout and runtime-smoke cases through their real
  public boundaries, and measure equivalent workload cost separately from CI.
- Update the existing terminal plan with the preceding delivery closure and the
  remaining fixture, startup, evidence-reuse and hosted-verification gaps.

## Capabilities

### Modified Capabilities

- `quality`: subject=source-observation; reuse=extend; change=modify

## Impact

The existing source identity, Git execution and closeout projection owners and
their regression tests change. No dependency, daemon, alternate state store,
adopter patch, new proof plane or parallel plan is introduced.

## Out Of Scope

- Caching mutable source identity across commands or bypassing index/content checks.
- Increasing pytest workers, test timeouts, ELOC ceilings or coverage exclusions.
- A global subprocess scheduler, latest-release discovery or complete P5 closure.
