## 1. Preserve the failing native fact

- [x] 1.1 Add a regression that requires Windows protection failure to preserve
  the child exit code and stderr; verify it fails against the accepted adapter.
- [x] 1.2 Implement bounded native error propagation in the existing adapter and
  verify the focused trust-anchor tests pass.
- [ ] 1.3 Publish the proved diagnostic object to `proposal/*` and capture the
  exact Hosted Windows failure without replaying a mutation.

## 2. Correct the native ACL operation

- [ ] 2.1 Correct the sole Windows ACL program from the observed native failure
  and add the smallest regression that distinguishes the repaired operation.
- [ ] 2.2 Verify real Windows protection and foreign-writer rejection across the
  Hosted Python matrix, plus affected local tests and static checks.

## 3. Close the successor

- [ ] 3.1 Run exact-HEAD full proof, official archive and archived reproof.
- [ ] 3.2 Complete candidate and accepted exact CAS, activate the immutable
  package runtime, publish `dev` then `main` to both peers, and verify Hosted CI.
- [ ] 3.3 Retire the Work Lane and verify ref, worktree, Lease, and proposal
  projection residue are absent.
