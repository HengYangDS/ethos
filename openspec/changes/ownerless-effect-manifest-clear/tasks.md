## 1. Exact retained-package boundary

- [x] 1.1 Bind all three source refs and heads, decision IDs, completion receipt
  IDs and SHA-256 values, manifests, bundles, and empty patch digests.
- [x] 1.2 Verify all three source branches and worktrees are absent, all bundles
  verify, and inventory reports each package as `retained`.
- [x] 1.3 Bind the accepted reconciliation authority and the completed dirty
  package clear as the predecessor boundary.

## 2. Clearance authority

- [x] 2.1 Add the exact Claim, Chronicle, structured package index, and OpenSpec
  delta.
- [x] 2.2 Require one native `lane_resolution/clear-preservation` invocation
  per exact decision and manifest while retaining decisions and receipts.
- [x] 2.3 Keep every valid-owner Work Lane and every unrelated package outside
  the mutation boundary.

## 3. Validation and archive closeout

- [x] 3.1 Pass strict OpenSpec, claims, package integrity, docs, and focused
  governance checks.
- [ ] 3.2 Commit, refresh generic parity, and execute exact-HEAD proof.
- [ ] 3.3 Officially archive, refresh post-archive parity, re-prove, land, and
  accepted-close this carrier.

## Post-archive transition boundary

After accepted local closeout, native clear may affect only the three exact
decision and manifest pairs in the Chronicle. Each dry-run, apply, clear receipt,
final inventory check, and owned-carrier retirement is a later transition rather
than an unfinished task in the archived Change.
