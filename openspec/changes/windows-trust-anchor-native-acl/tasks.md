## 1. Preserve the failing native fact

- [x] 1.1 Add a regression that requires Windows protection failure to preserve
  the child exit code and stderr; verify it fails against the accepted adapter.
- [x] 1.2 Implement bounded native error propagation in the existing adapter and
  verify the focused trust-anchor tests pass.
- [x] 1.3 Define proposal publication and Hosted observation as post-archive
  external verification, not implementation work that would make this Change
  impossible to complete before it can enter the candidate role.

## 2. Prove the diagnostic atom

- [x] 2.1 Pass the focused trust-anchor tests, Ruff, format validation, and strict
  OpenSpec validation.
- [x] 2.2 Freeze the signed source commit and pass affected and full exact-HEAD
  proof.

## 3. Close the diagnostic Change

- [x] 3.1 Confirm archive readiness with no unresolved implementation or local
  verification task remaining.
