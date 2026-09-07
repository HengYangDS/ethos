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
