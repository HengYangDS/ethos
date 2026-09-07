## Context

The user requirement is at least 95 percent coverage. Commit `efa43b9f` changed
the executable floor to 93, leaving 95 as an unused aspiration. The current
architecture test derives its expected threshold from that same mutable policy;
it proves projection consistency but cannot detect this requirement violation.
Default proof and local CI do not currently select the floor gate.

## Goals / Non-Goals

Restore the requirement and close its existing execution paths. Measure the
whole declared Python product with branches enabled; preserve meaningful
behavior, assertions, existing budgets, and exact-HEAD freshness. Do not widen
this Change into a generic policy engine or unrelated lifecycle redesign.

## Decisions

1. Keep `.config/checks/coverage/policy.toml` as the sole executable threshold
   declaration. Restore `current_hard_floor = 95`; remove the unconsumed
   `aspirational_floor`. The native coverage config continues to own measurement.
   A second threshold file or a hard-coded runtime minimum would add parallel
   configuration rather than fix the requirement.
2. Reuse `PythonTestGate.enforce_floor` and the dependent `coverage-floor` gate.
   Add the gate to default proof and run its existing Nox session immediately
   after tests in local CI. Never rerun tests merely to evaluate the same data.
3. Exercise the real gate against isolated coverage data just below and at the
   floor. Expectations are independently chosen 94/95 boundary outcomes, not
   copied from the declaration. Preserve the freshness and native-config checks.
4. Use the current coverage report to locate unproved authority, failure, and
   cleanup behavior. Extend existing scenario tables and consolidate repeated
   setup before adding test surface. Deletion is justified by redundant semantic
   ownership, not a desired denominator. No omit, pragma, branch disabling,
   synthetic execution in product proof, or budget relaxation is remediation.
5. Correct requirement and carrier descriptions in their existing owners. The
   terminal route records the acceptance hold and execution order; OpenSpec
   tasks record actions and progress only. Historical attestations remain true
   observations under their then-configured floor, not evidence of compliance.
6. Close the archive-compensation defect exposed by the behavior tests at its
   existing owners. Reuse the canonical archive-root grammar to bind the exact
   Change and path independently of command success: a failed command may still
   return a positively bound cleanup path, but malformed or foreign coordinates
   cannot. The Git effect owner rejects root equality, path traversal, symlink
   and junction components, and tracked targets before recursive removal. After
   restoring the pre-effect tree, re-observe the worktree; unowned residue stays
   intact and causes the existing retained-residue outcome, not a success claim.
   Exercise destruction only within disposable fixture roots. This is a bounded
   correction of measured failure behavior, not a new cleanup service or state.

7. Generation retirement needs complete current-consumer observation, not merely
   the readable subset. The existing activation owner distinguishes genuinely
   absent roots from linked, unreadable, or non-directory paths using non-following
   metadata. Traverse real directories with error-propagating enumeration; read
   only regular files, reject symlinks/junctions and unsupported kinds, and fail
   closed on missing nested entries, scan failures, or invalid text. Preserve
   selector, state, and every generation when initial observation is unknown.
   Reuse the same observer during cleanup planning; add no registry or second
   liveness model. Isolated static-path regressions do not prove filesystem-race
   or new-consumer-after-observation safety.

8. Compensate only resources created by the current start invocation. Lease
   acquisition returns its creation disposition; existing native worktree
   Attestations distinguish applied creation from recognition. Reused resources
   never become deletion targets on provenance, holder, or hook failure. An
   unreceipted new path is unknown, not owned; retain it and the supporting ref
   and Lease. Remove proved new worktrees without force so later user content
   blocks cleanup. A failed removal retains dependent ref/Lease state, and a
   failed exact Lease revocation retains the ref. Reuse the existing four-field
   Lease revocation owner, deleting the start adapter's duplicate SQL that omitted
   expiry. No persistent creation registry or second recovery protocol is added.
   These synchronous compensation cases do not establish process-crash recovery
   or protection against arbitrary concurrent filesystem replacement.

## Risks / Trade-offs

The restored gate initially fails. That is the correct outcome until actual
coverage is sufficient, not a reason to weaken it. Existing default proofs no
longer satisfy the expanded required gate set. Test growth must remain within
its own source budget; unrelated code deletion cannot offset a local violation.

## Migration / Verification

Reuse the owned missing-Lease Work Lane with this fresh official Change; retain
its archived predecessor byte-for-byte. First obtain exact-path prewrite, watch
the boundary regression fail at 93, restore the owner and execution selection,
and verify focused GREEN. Then close measured behavior gaps and run full proof
once on frozen source. Archive/reproof and candidate/accepted CAS remain blocked
until coverage is at least 95. Runtime readback and historical-lane retirement
resume only after that acceptance, following the existing terminal route.
