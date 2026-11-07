# Tasks

## 1. Removal

- [ ] 1.1 Remove `distributions/npm`, its test and the root `ethos` and `test:npm` scripts, and drop
      the launcher from JavaScript coverage. Done when `javascript-tests` passes and no tracked file
      outside history names `distributions/npm`.
- [ ] 1.2 Reduce the release identity to the `VERSION` carrier with the root Node manifest guard,
      and the product boundary and format selection to the root rules. Done when the release,
      boundary and format-selection tests pass with their launcher cases removed.
- [ ] 1.3 Let the semantic closure treat a bare word as prose, not as a reference to an emptied
      directory, and drop the stale `distributions` entries. Done when a closure test shows that a
      docstring word is not a consumer while a `legacy/` literal is, and the product boundary
      passes.

## 2. Documents and acceptance

- [ ] 2.1 Update the README, the release guide, the distribution explanation and the changelog.
      Done when the docs gates pass.
- [ ] 2.2 Pass lint, the full suite and readiness at the lane head. Done when each passes on the
      committed head.
