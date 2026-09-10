## Why

Verification feedback is both slow and difficult to inspect. Recent local full
proofs took roughly 17--19 minutes. A single module accounts for nearly the
entire test critical path under scope-based scheduling. Both hosted templates
upload proof receipts but omit the JUnit and coverage artifacts their test
owner already produces. Report absence hides failures instead of preventing them.

## What Changes

- Reuse native pytest work stealing for independent test items, preserving
  declared worker limits, the exact workload and the coverage floor.
- Publish existing JUnit and coverage outputs on both Forge projections,
  including failed runs; expose GitLab test reports and a GitHub job summary.
- Test transport and failure behavior through existing quality owners.
- Update the existing terminal plan with measured bottlenecks and the unified
  review of constraints, policy, transitions, effects and evidence reuse.

## Capabilities

### Modified Capabilities

- `quality`: bounded test scheduling and visible, source-bound test feedback.

## Impact

Existing Python test execution, hosted proof transport, CI templates and their
checked projections, focused tests and the terminal execution plan. No new
runtime, plugin registry, roadmap, authoring lane or third-party action.

## Out of Scope

- Reusing proof across changed HEADs without a separately proved input closure.
- Installing CUE, a state-machine framework, telemetry backend or workflow engine.
- Broad fixture redesign or weakening coverage, identity, authorization or budgets.
- Claiming remote publication or a speed improvement before measuring it.
