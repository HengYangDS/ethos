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
- [ ] 3.2 Land and complete the permitted local closeout on a current candidate
  base; do not push or mutate remote state.
- [ ] 3.3 After acceptance, re-observe the target and execute native dry-run
  then apply only if exact policy and residue still match; verify receipt and
  lease absence.
- [ ] 3.4 Retire this carrier and the prior recovery carrier only through their
  owner-bound native retirement paths after both are clean and retire-ready.

## Post-archive transition boundary

This archive records completed authoring and validation only. Candidate land,
accepted-root local closeout, target re-observation, native lease-only
reconciliation, and both carrier retirements remain separately gated and must
not be inferred from this archived checklist.
