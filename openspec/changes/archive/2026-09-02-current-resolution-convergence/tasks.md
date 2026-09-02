## 1. Contract and RED

- [x] 1.1 Modify the command-plane requirement for single-resolution archive planning and validate the official Change strictly.
- [x] 1.2 Add failing regressions proving archive readiness and plan compilation cannot reread OpenSpec governance or reload Commitment.
- [x] 1.3 Add a failing regression proving staged archive recovery compiles intent from the exact source HEAD through `CurrentResolution`.

## 2. Replacement and deletion

- [x] 2.1 Extend `CurrentResolution` with exact committed-source selection and verify current-resolution tests.
- [x] 2.2 Route archive orchestration and effect-plan compilation through one resolved Commitment, then delete archive-local governance and Commitment fallbacks.

## 3. Closure

- [x] 3.1 Run focused lifecycle tests, repository-wide reference closure, Ruff, typing, module-layout, and strict OpenSpec validation.
- [x] 3.2 Freeze the final implementation diff and verify that the current public command plane reports no pre-commit governance gap.

## Lifecycle Transition Boundary

After every task above is complete, the implementation requires a signed commit
and exact-HEAD full proof before official archive. Archive creates a distinct
signed HEAD that then requires reproof, candidate and accepted exact CAS, fresh
immutable-runtime readback if affected, and retirement of this Work Lane. These
are mandatory terminal transitions after the checklist, not self-referential
pre-commit tasks, and MUST NOT be claimed before their exact observations exist.
