# Tasks

- [x] 1.1 Add RED package-level proposal dry-run and receipt-bound apply tests.
- [x] 1.2 Add RED local-only, single-peer, repeated-provider, and multi-peer
  topology tests.
- [x] 1.3 Add RED remote drift, partial-effect, and idempotent retry tests.
- [x] 1.4 Compile proposal targets into one `TransitionPlan` and execute only
  its admitted exact-CAS effect.
- [x] 2.1 Remove single-peer result aliases, duplicate validators, and the
  publication-specific state tree.
- [x] 2.2 Keep contracts, mutation adapter, declaration compiler, domain
  reducer, and CLI projection MECE; delete ownerless abstractions and tests.
- [x] 2.3 Make prose execution consume its declared policy owner only.
- [x] 3.1 Set `python_tests = 36000` and retain the 95% coverage floor.
- [ ] 3.2 Run focused, broad, Ruff, Ty, config, source-budget, and package-only
  gates on the governed lane.
- [ ] 3.3 Create signed atomic commits and execute exact-HEAD full proof.
- [ ] 3.4 Archive, run post-archive proof, governed land and accepted closeout,
  then emit a source-independent accepted runtime receipt.
