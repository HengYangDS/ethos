## Why

The hosted `repository proof` runner exercises an isolated checkout where Work
Lane coordination details are exact, while an existing product test hard-codes
the bounded-reader `deferred` state. That test confuses a permitted observation
mode with a product invariant and turns a correct vendor-neutral read model into
a hosted-only failure.

## What Changes

- Make the orientation and status projection tests derive `detail_state` and
  dependent counts from the observed coordination payload.
- Add an isolated-repository regression proving that `exact` coordination detail
  remains valid when no foreign Work Lanes are present.
- Clarify the Work Lane Coordination Read Model so `deferred` is a bounded-reader
  observation mode, not a universal contract.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=coordination-detail-read-model; reuse=extend;
  change=modify; facet:lifecycle=validation; facet:surface=cli,openspec,ci;
  facet:authority=source,test,openspec,claim,evidence — clarify the coordination
  detail-state contract for bounded and full readers.

## Out Of Scope

- No provider-, forge-, IDE-, or vendor-specific execution behavior.
- No change to lease authority, handoff, retirement, or foreign-lane permissions.
- No expansion of bounded readers into full foreign Work Lane inventories.

## Impact

Affected surfaces are the `orient`/`status` product tests and the repository
-governance OpenSpec delta. There is no provider-specific behavior, no change to
lease authority, and no change to Work Lane lifecycle semantics.
