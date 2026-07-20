## Why

Bounded repository readers deliberately skip foreign Work Lane path, dirty,
relation, and closeout detail. When no foreign Work Lane is visible, the current
aggregation infers `detail_state=exact` from `any([]) == false` and fabricates
five exact zero aggregates even though the caller selected the deferred mode.

## What Changes

- Make the full-versus-bounded coordination detail mode an explicit caller
  input instead of inferring it from foreign-lane rows.
- Keep a zero-foreign-lane bounded read at `detail_state=deferred` with the five
  detail-dependent aggregates set to `null`.
- Keep a zero-foreign-lane full read at `detail_state=exact` with those five
  aggregates set to zero.
- Add a focused zero-inventory regression before changing production code.
- Restore the concurrently weakened status/orient assertions and archive the superseded active claim without rewriting its historical OpenSpec archive.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=work-lane-coordination-empty-inventory; reuse=extend; change=modify; facet:lifecycle=validation,runtime; facet:surface=cli,test,openspec,evidence; facet:authority=source,test,openspec,claim,evidence

## Impact

- Coordination aggregation and its `workspace_status` caller.
- Focused lane-status and status/orient regressions, the repository-governance
  specification, active correction claim, superseded claim/Chronicle, and
  generic parity evidence.

## Out Of Scope

- Do not weaken status/orient expectations; restore the concurrently accepted
  exact-empty assertions to the preceding bounded `deferred` contract.
- No schema, command, provider, orientation, or public JSON shape expansion.
- No remote publication, hosted-CI success, candidate landing, accepted-root
  closeout, or foreign Work Lane mutation claim.
