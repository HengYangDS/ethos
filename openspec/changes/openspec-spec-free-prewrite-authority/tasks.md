## 1. Regression

- [x] 1.1 Add a compiler regression proving that a valid planned `skip_specs: true` Change compiles while implementation tasks remain incomplete.
- [x] 1.2 Add a digest regression proving that changing only task checkbox progress does not change the compiled Commitment.

## 2. Authority Convergence

- [x] 2.1 Remove task-completion state from spec-free Commitment compilation, normalize only task checkbox markers before hashing, and delete obsolete apply-progress plumbing.
- [x] 2.2 Verify current resolution and exact-path prewrite admit bounded product writes for the planned spec-free Change while malformed or incomplete official artifacts still fail closed.

## 3. Verification And Closeout

- [x] 3.1 Run focused compiler, current-resolution, and prewrite tests plus strict OpenSpec and affected static gates without warnings or errors.
- [x] 3.2 Verify repository-wide reference closure: spec-free Commitment compilation has no task-completion input, no `instructions apply` dependency, and no duplicate tracked acceptance carrier.
