## 1. Contract and reproduction

- [x] 1.1 Record the exact ref-preserved, worktree-absent, valid-Lease residual
  state and its missing public convergence path.
- [x] 1.2 Prove that ordinary archive-equivalent retirement succeeds through
  installed hooks, isolating recovery rather than generic permission as the
  product defect.

## 2. Public recovery transition

- [x] 2.1 Add an explicit path coordinate to superseded retirement and compile
  a recovery target only from exact ref, Lease, holder, tree, Commitment, path,
  and absorption facts.
- [x] 2.2 Recreate the exact linked worktree through the native worktree-effect
  owner and resume the existing linked retirement transaction.
- [x] 2.3 Preserve structured recovery evidence and leave a recovered worktree
  available when a later retirement effect blocks.

## 3. Verification

- [x] 3.1 Cover successful package-style recovery and retirement plus path
  collision, foreign holder, stale tree, and moved-coordinate negatives.
- [ ] 3.2 Run focused retirement and CLI tests, formatting, lint, OpenSpec,
  source budget, and the unchanged 95 percent coverage floor.
- [ ] 3.3 Execute exact-HEAD full proof, archive, post-archive proof, governed
  land, accepted closeout, and immutable package-only runtime verification.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| `repository-governance:Linked Work Lane retirement has one generation-bound effect` | `2.1` | `tests/unit/lanes/lease/test_lease_lifecycle.py::test_superseded_retirement_recovers_exact_unbound_lease_then_retires` |
