## Context

Accepted `dev`, `candidate/dev`, and `main` are aligned at
`b675cd64e79fa4e35000d8efd2b03465a0ab55fb`. Native direct-retire admission for
an exact missing-lease budget predecessor reached
`lane_resolution_ownerless_state_unverifiable` without a package, receipt,
reservation, fence, ref, or worktree effect.

The canonical lease schema is valid. The two exact ownerless targets have
valid expired rows, while unrelated historical rows carry legacy payload
shapes that do not satisfy the current `LaneLease` contract. The state-store
helper reads and strictly validates the whole table and only then compares
`lease.lane_ref` to the requested subject. This allows unrelated row damage to
control an exact target decision.

## Goals / Non-Goals

**Goals:**

- Make ownerless closeout lease reads exact-subject scoped at the SQL boundary.
- Keep the exact target row and global schema strictly fail-closed.
- Use one validator in read observation and transactional fence acquisition.
- Prove the native admission path reaches later target checks when only an
  unrelated legacy row exists.
- Bind one fresh post-acceptance direct-retire probe for each of the two exact
  missing-lease budget predecessors without reviving earlier decisions.

**Non-Goals:**

- No lease cleanup, migration, schema change, compatibility projection, public
  surface, prior-decision reuse, premature disposition change, valid-owner
  mutation, remote work, or broad housekeeping.

## Decisions

1. **Filter at the storage boundary.** Replace the whole-table helper with an
   exact-subject helper whose SQL uses `where subject = ?`. Do not iterate the
   full table and skip invalid rows after parsing; that would mix unrelated
   state into the decision and could accidentally hide malformed target data.

2. **Keep validation strength unchanged.** Validate the canonical lease schema
   before querying. Pass every returned exact row through the existing strict
   raw-row, JSON, type, holder, time, identity, coordination-scope, and
   authority checks. A malformed exact row remains unverifiable for observation
   and conservatively blocks fence acquisition.

3. **Share one exact-row validator.** Both `_has_unexpired_lease` inside the
   `begin immediate` transaction and `_closeout_state_snapshot` in read-only
   observation use the same helper. This prevents read/admit drift.

4. **Use equality, not prefix matching.** A successor or similarly named branch
   is unrelated unless its complete `subject` equals the requested target.

5. **Do not repair state as a side effect.** This Change performs no
   `update`, `delete`, migration, or recoding of lease rows. Maintenance and
   inventory retain their existing whole-store semantics.

6. **Issue successor probe authority with the repair.** Two target-specific
   Chronicles retain the exact `lane_resolution/retire` token, branch, and
   HEAD. The first binds decisions `lane-decision:6e57ce11-5723-4171-85a8-596452f118fa`
   and `lane-decision:97d3e6ae-f0d4-41f0-a236-efa3896383c5` as immutable
   no-effect records; the second supersedes its earlier unconsumed retry Claim.
   Each successor authorizes one new decision only after this code repair is
   accepted. An accepted-ancestor refusal remains no effect and must precede a
   separate preserve-retire reconciliation.

## Risks / Trade-offs

- **Exact target row is malformed** -> Preserve fail-closed behavior; do not
  project it as absence.
- **Lease schema is invalid** -> Stop before target observation.
- **A current exact lease or Claim exists** -> Keep the target coordinated and
  block ownerless closeout.
- **Only unrelated legacy rows exist** -> Exclude them from this exact target
  decision; their separate maintenance status remains unchanged.
- **A stale decision is retried** -> Reject it through the existing observation
  and Chronicle bindings; this code fix does not revive prior decisions.

## Migration Plan

1. Add the carrier and RED regression tests.
2. Apply the smallest helper/query change and prove RED-to-GREEN.
3. Run focused and changed-scope gates, refresh tracked generic parity, execute
   exact-HEAD proof, archive, land, accepted-close, and retire this carrier.
4. Only after acceptance, create the two target decisions from fresh
   observation; preserve any later no-effect result for a separately accepted
   reconciliation.

Rollback before land is to discard only this owned Work Lane. After land, a
regression requires a new governed successor; manual SQLite or foreign-lane
mutation is never a rollback path.

## Open Questions

None. Target lease state, Git observation, accepted ancestry, and decision
freshness remain execution-time predicates.
