## 1. Native reconciliation contract

- [x] 1.1 Add ref-absent observation and policy admission bound to the exact
  owner-unavailable lease tuple, absent source worktree, current accepted
  policy, and immutable prior native attempt.
- [x] 1.2 Add no-clobber reconciliation attempt/receipt records and execute only
  the exact native lease-generation CAS after pre-effect re-observation.
- [x] 1.3 Make ordinary exceptional protected-ref transaction guards
  hook-compatible through same-value CAS updates.

## 2. Public surface and regression proof

- [x] 2.1 Expose the explicit nested `lane retire reconcile-ref-absent` CLI
  command and bind actual invocation holder identity in its mutation envelope.
- [x] 2.2 Cover successful reconciliation and fail-closed ref, worktree, lease,
  prior-attempt, and Chronicle drift cases.
- [x] 2.3 Add CLI, documentation, registry, canonical OpenSpec, Claim, and
  Chronicle carriers for the target-specific transition.

## 3. Lifecycle closeout

- [x] 3.1 Run focused tests, lint/types, strict OpenSpec, changed-scope plan,
  and parity before committing the archived carrier; exact-HEAD proof follows on
  the committed carrier.

## Post-archive transition boundary

This archive records completed authoring and validation only. Candidate land,
accepted-root local closeout, target re-observation, native lease-only
reconciliation, and both carrier retirements remain separately gated and must
not be inferred from this archived checklist. They are post-archive lifecycle
transitions, not incomplete archive tasks: local closeout requires a current
candidate; reconciliation requires a fresh exact-residue admission; and each
carrier retirement requires its owner-bound native lifecycle path. No remote
push or hosted-CI claim is authorized by this archive.
