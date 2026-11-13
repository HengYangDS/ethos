# Tasks

## 1. README role and bound

- [x] 1.1 Report a non-index README and an index over 100 nonblank lines. Done when each gap's test
      failed before the change, a short index passes, and the docs health tests pass. Evidence: red
      at 10:54:40, before the implementation: the `policy` and `long-index` cases of
      `tests/unit/governance/test_docs_readme_index.py` failed and the short index passed. Green at
      10:56:41 in `f7133c4df`: 442 passed over the 17 test files that reach docs health and the docs
      registry.
- [x] 1.2 Drop "semantic boundary" from `docs/governance/docs-registry.md` and add the CHANGELOG
      Breaking line. Done when the docs gates pass on the changed pages. Evidence: in `f7133c4df`
      Prettier and Vale accepted `docs/governance/docs-registry.md` and `CHANGELOG.md` at commit
      time, 10:57:24.

## 2. Acceptance

- [ ] 2.1 Pass readiness and the precheck at the lane head. Done when each passes on the committed
      head.
