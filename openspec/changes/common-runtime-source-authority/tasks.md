## 1. Reproducer

- [x] 1.1 Add a linked-worktree regression in which the invoking repository has
  a valid current profile while one historical checkout has an invalid profile;
  prove the incumbent installer rejects the otherwise valid common activation.

## 2. Single source authority

- [x] 2.1 Resolve the expected runtime source identity once from the invoking
  repository and pass it to every linked-worktree and final binding observation.
- [x] 2.2 Delete per-worktree expected-source interpretation from the activation
  transaction and prove accepted-authority failure still blocks before mutation.

## 3. Closeout

- [x] 3.1 Run format before lint, focused hook/runtime tests, strict OpenSpec
  validation, and changed proof readiness.
- [ ] 3.2 Run the full applicable proof on the frozen HEAD, then archive, land,
  close out, install the accepted runtime, and prove a second install idempotent.
