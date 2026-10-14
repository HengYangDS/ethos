# Tasks

## 1. Reproduce

- [x] 1.1 Add a real-Git lane start regression that fails, compensates and retries the identical plan; verify it reports `git_effect_attestation_content_mismatch` before the fix.
- [x] 1.2 Add an executor regression for an attested exact inverse and a forged inverse; verify both retries block before the fix.
- [x] 1.3 Add a lane-birth case with a compensated start followed by a later start; verify it reports `openspec_change_provenance_unresolved` before the fix while the unattested deletion case stays ambiguous.

## 2. Closure

- [x] 2.1 Define the exact inverse once on the Git effect contract and derive the executor's reverse transaction and Work Lane start compensation from it; verify the existing executor and lane start tests pass.
- [x] 2.2 Exclude an Attestation closed by a later validated exact inverse from exact-plan recognition; verify the retry regressions pass, every Attestation stays in the set, and the forged inverse still blocks.
- [x] 2.3 Exclude a compensated start from the lane-birth boundary; verify the restart case selects the lane's Change and the unattested deletion case remains ambiguous.

## 3. Verify

- [x] 3.1 Run strict OpenSpec validation, Ruff, ty, the code-size gate and the affected unit and architecture tests; verify no failure beyond those of the unchanged base in the same environment and no unrelated tracked file change.

## Workflow follow-up

- Prove the exact lane head, land and close it out through the ordinary lifecycle, then retire the lane and archive this Change.
- The adopter recovers once it selects a runtime containing this change.
