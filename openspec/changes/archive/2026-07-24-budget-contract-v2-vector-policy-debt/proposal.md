# Budget Contract v2 Vector Policy And Debt

## Why

Task 4 now provides immutable Git snapshot/replay and a fail-closed shadow, but
it does not provide a complete v2 baseline vector: the accepted C1 checkpoint
still has the exact YAML provider gap and therefore a null v2 observation.
Budget Contract v2 nevertheless needs strict policy and debt contracts plus a
pure reducer before changed-scope admission can be implemented.

The repository must not convert v1 scalar/category debt into cross-coordinate
headroom or infer a historical admitted HEAD from commit order. The sole v1 debt
record therefore remains an explicit blocking `unmapped` successor while the
repository v2 policy remains `inactive`.

## What Changes

- Add strict coordinate, vector, baseline-binding, wave, mapped-debt, unmapped-
  debt, inactive-policy, and shadow-policy contracts.
- Promote the accepted Task 4 shadow observation to a public typed envelope and
  consume it directly from the pure verdict reducer.
- Add a pure `compile_budget_verdict(observations, policy, today)` reducer with
  logical-AND coordinate evaluation, no cross-unit or cross-scope compensation,
  fail-closed replay trust checks, inclusive date boundaries, and deterministic
  output.
- Add a sibling `[quality.source_budget_v2]` loader and an explicitly inactive
  repository declaration without changing `[quality.source_budget]` behavior.
- Publish a versioned JSON Schema composition admitting the existing v1 union
  and the new v2 union.
- Preserve the node-runtime v1 record as `unmapped` with missing admitted-head,
  scope, inventory, baseline-snapshot, and historical-replay bindings.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `contracts`: subject=budget-contract-v2-vector-policy-debt;
  reuse=extend; change=modify;
  facet:lifecycle=authoring,validation,migration;
  facet:surface=contract,config,schema,evidence;
  facet:authority=source,test,config,openspec,claim,evidence.
- `quality`: subject=budget-contract-v2-vector-policy-debt;
  reuse=extend; change=modify;
  facet:lifecycle=authoring,validation,migration;
  facet:surface=policy,reducer,report,evidence;
  facet:authority=source,test,config,openspec,claim,evidence.

## Impact

This Change adds bounded contracts, a pure reducer, focused adversarial tests,
an inactive repository declaration, schema/config projections, and reviewed
evidence. V1 source-budget output and enforcement remain authoritative.

## Out Of Scope

- Task 6 changed-scope admission or a new default gate.
- Inferring or fabricating a complete v2 baseline, terminal vector, or mapped
  node-runtime allowance while the YAML replay remains incomplete.
- DR-0009 calibration, dual control, v2 authority, global v1 LOC retirement,
  terminal settlement, remote publication, or hosted execution claims.
