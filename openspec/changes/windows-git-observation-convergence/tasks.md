## 1. Regression

- [ ] 1.1 Add a focused regression that creates the generated adopter under a
  temporary global `core.autocrlf=true`, checks out ordinary tracked text as
  CRLF, proves ambient Git reports clean, and verifies `dirty_provenance()`
  reports clean without ambient configuration.

## 2. Repository-Local Text Authority

- [ ] 2.1 Update the generated adopter's existing `.gitattributes` owner with
  canonical LF semantics for ordinary text while retaining exact-byte LF/CRLF
  probes, and verify the focused regression plus existing line-ending test pass.

## 3. Verification And Closeout

- [ ] 3.1 Run the focused package-acceptance and Git-observation tests, strict
  OpenSpec validation, and the smallest affected quality gates with no warnings
  or errors.
- [ ] 3.2 Freeze a signed commit, run exact-HEAD full proof, archive and reprove
  the official Change, advance candidate and accepted through exact CAS, read
  back the immutable package runtime, and obtain fresh native Windows hosted
  evidence before retiring the absorbed Work Lane.
