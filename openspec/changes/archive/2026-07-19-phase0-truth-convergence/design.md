## Context

The official OpenSpec boundary owns the active Change, validation, delta, and
archive workflow. ETHOS owns repository-local mutation admission, coverage
evidence semantics, bounded reader projections, hard-quality classification,
proof readiness, and local publication decisions.

The current defects share one root cause: a projection treats absent
observation as positive evidence. Directory existence is treated as a live
coverage writer; uninspected foreign worktrees are counted as clean; and an old
HEAD-bound proof record is allowed to hide current local-state hard-quality
failures. The repair therefore introduces no new truth store. It tightens the
existing observations and reuses one hard-quality report across the decision
surfaces.

## Design

### Coverage writer state

The coverage reader classifies the lock as `absent`, `active`, `dead`, or
`invalid`. `active` requires a parseable owner file, a live PID, and an exact
process-start fingerprint. Only that state may suppress the stale
missing-artifact diagnostic, and it replaces it with the blocking
`coverage_artifact_write_in_progress` gap. Dead, missing-owner, malformed, and
PID-reused locks retain `coverage_artifact_missing` and expose lock-state
diagnostics.

The shell owner script keeps immediate reclamation for a proven dead/reused
owner. Missing or malformed owner metadata is not preempted during the normal
acquisition window, because another process may be between `mkdir` and owner
write. After the bounded wait expires, one persistently invalid lock may be
removed and acquisition retried. A valid live owner is never preempted.

### Bounded coordination readers

Full `ethos lane status` retains exact integer aggregates. Bounded readers keep
the cheap foreign-lane inventory and lease facts but emit
`detail_state=deferred`; dirty, overlap, unknown-scope, and closeout aggregate
counts become JSON null. Summary declarations preserve null and add the detail
state. Human output directs the operator to `ethos lane status --json` instead
of describing deferred detail as clean.

### Local readiness convergence

Generated-artifact topology joins the product hard-quality floor. `report`
already consumes that floor, and enterprise readiness consumes the report plus
its direct generated-artifact layer. Product `publish` will consume the same
hard-quality floor before declaring local readiness. Adopter publication keeps
its profile-owned quality boundary.

Executed proof remains necessary but not sufficient: a current proof record
cannot override a current local-state hard-quality blocker. Source-budget stays
in the explicitly non-blocking global-compression layer for this Change.

## Alternatives

- Treat an empty lock as an advisory: rejected because it both hides missing
  evidence and prevents the owner test gate from starting.
- Scan every foreign worktree in `status`: rejected because it removes the
  bounded-reader performance contract. Explicit unknown state is cheaper and
  truthful.
- Make `publish` call the complete scorecard: rejected because the scorecard is
  large and would create an avoidable surface dependency. Reuse only the
  product hard-quality reducer.
- Promote source-budget to P0 in the same Change: rejected because it is an
  independently governed compression program and would prevent a focused
  truth repair.

## Proof Strategy

1. Red/green unit tests for empty, malformed, dead, PID-reused, and live writer
   locks.
2. Shell regression coverage for invalid-lock reclamation after the bounded
   wait and live-owner non-preemption.
3. Schema and reader tests proving bounded null/deferred aggregates and exact
   full-lane integers.
4. Report and publish tests proving current generated-artifact and coverage
   gaps block local readiness.
5. Focused quality gates, OpenSpec lifecycle, generic parity, full owner test
   gate, HEAD-bound proof, archive, candidate land, and accepted-root closeout.

Rollback is a normal Git revert before publication. If the stricter state
classification exposes previously hidden blockers, those blockers are retained
rather than weakened to recover a green scorecard.
