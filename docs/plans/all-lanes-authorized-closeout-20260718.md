---
subject: ethos:all-lanes-authorized-closeout-20260718
role: plan
state: archived
relations:
  implements: all-lanes-authorized-closeout-20260718
  derives_from: all-work-lanes-convergence-program-20260716
---

# Authorized Work Lane Cohort Closeout — 2026-07-18

Status: archived after HEAD-bound proof; candidate and accepted-root closeout are in progress.

Purpose: move the currently observed ETHOS `work/*` cohort to an exact,
evidence-bound local outcome without claiming foreign ownership, remote
publication, or hosted verification.

See also: [Product Design Contract](../governance/product-design-contract.md)
and the [archived OpenSpec Change](../../openspec/changes/archive/2026-07-18-all-lanes-authorized-closeout/).

This is a two-level program.  The current Work Lane promotes the governance
decision first.  Only after its accepted-root closeout may separately admitted
successor lanes perform an exact preservation, handoff, exceptional resolution,
semantic replay, or retirement effect.

## Frozen Decision Snapshot

The current full `ethos lane status --json` observation is tracked at
`evidence/chronicle/all-lanes-authorized-closeout-20260718/current-lane-matrix.json`.
It is a read-only snapshot, not reusable authority.  At its observation time it
contains 64 foreign lanes, 34 missing leases, 14 dirty foreign lanes, two clean
accepted ancestors, two accepted descendants, and one diverged unbound ref.

The matrix groups the 64 foreign lanes into:

| Initial route | Count | Required next condition |
| --- | ---: | --- |
| Holder handoff then `retire landed` | 2 | Exact holder or accepted handoff, clean HEAD recheck. |
| Holder handoff then normal current-lifecycle land | 2 | Fresh proof, candidate land, accepted closeout. |
| Holder handoff then dirty-overlay preservation | 7 | Exact preservation before any semantic or retirement choice. |
| Holder handoff then semantic review | 19 | Current-candidate, test-first intent extraction. |
| Accepted exception then focused replay | 15 | Accepted Chronicle decision and exact fresh target observation. |
| Accepted exception then focused replay or block | 7 | Family-specific policy/assurance/remote boundary decision. |
| Missing-lease dirty preservation routes | 7 | Bundle/manifest verification before any exception apply. |
| Family decision remains blocked | 5 | No path to retirement until non-linear lineage is resolved. |

The unbound `work/adopter-material-scope-bootstrap-20260715` is separately
preserve-or-replay work; it is never a raw ref-deletion candidate.

## Phase A — Promote the Decision Carrier

1. Re-run full lane status immediately before every tracked decision update.
   Use bounded `status` only for root readiness; it defers foreign path/dirty
   expansion and cannot certify a foreign worktree clean.
2. Bind the matrix, semantic audit, OpenSpec scope, claim, dated Chronicle, and
   this plan to the current owned lane.
3. Run strict OpenSpec lifecycle, claim/schema checks, changed-scope planning,
   parity if required, and HEAD-bound executed proof.
4. Archive this Change, land it to `candidate/dev`, and run accepted-root
   closeout.  The resulting accepted Chronicle is the only decision foundation
   consumed by later exceptional lane-resolution actions.

## Phase B — Preserve and Resolve Exact Targets

For one target at a time, observe `branch`, `HEAD`, worktree status provenance,
lease ID/epoch/holder, claim binding, accepted relation, and semantic path
comparison.  A changed target invalidates the previous decision.

1. **Active normalized lease:** obtain a normal offer/accept handoff after
   holder quiescence, or leave it blocked.  A claim-missing active lease is not
   an orphan and does not authorize exception cleanup.
2. **Missing/ambiguous lease:** use the accepted Chronicle-backed native
   `lane resolution decide` then `lane resolution apply` path, with one target,
   one exact observation, reason, evidence references, recovery plan, and the
   irreversible confirmation required by the disposition.
3. **Dirty or unbound target:** make a content-addressed preservation package
   first.  It contains the exact source/accepted heads, lease/claim observation,
   porcelain/name-status, separate staged and unstaged binary patches, an
   archive plus hashes for untracked content, scope comparison, manifest digest,
   and receipt.  Never use `git stash`.
4. **Semantic residual:** extract the smallest missing behavior and focused
   regression into a current-candidate successor lane.  Historical branch
   topology is evidence only; whole-branch merge/cherry-pick is prohibited.

## Phase C — Replay and Close Each Owned Semantic Unit

1. Start or enter one admitted successor lane for one reviewable family.
2. Run exact `prewrite`, write a failing focused regression, implement the
   smallest current-contract behavior, and run focused/adjacent tests.
3. Refresh parity evidence whenever its semantic tree changed, then run
   `status -> plan -> prove --execute -> land`.
4. Perform accepted-root closeout only through the sanctioned command, recheck
   `dev == candidate/dev`, and retain the HEAD-bound proof record.
5. Retire only a clean, current, exact lane through the native landed or
   superseded command.  Otherwise retain a verified preserve-retire or block
   receipt with the next condition.

## Phase D — Final Local Publication Evidence

After the final local accepted HEAD is stable, refresh `run-local-ci.sh`
fallback evidence and re-run `status`, `report`, and `publish`.  The result may
claim local readiness only.  Remote probe/reconciliation, push, and hosted CI
remain separate, expressly unperformed stages requiring further authorization.

## Anti-Stall Execution Contract

- Every long command writes a bounded temporary log and receipt, records PID,
  exit code, completion time, and parsed JSON result, and has a timeout.
- Shadow parity resolves the checkout-bound `build/runtime/venv` before a
  legacy root `.venv`; a stale compatibility environment cannot make a current
  Work Lane appear unable to run ETHOS.
- Effects are serial; audit work can parallelize, but two irreversible lane
  transitions never race in the shared Git common directory.
- Every apply follows `fresh observe -> dry run -> exact apply -> receipt ->
  re-observe`; no terminal UI wait state is treated as evidence of completion.
- An unavailable or moving target is a real blocking fact for that target, not
  a reason to stall unrelated audit, preservation, or accepted-decision work.
