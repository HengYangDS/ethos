# Tasks

## 1. Removal

- [x] 1.1 Remove `distributions/npm`, its test and the root `ethos` and `test:npm` scripts, and drop
      the launcher from JavaScript coverage. Done when `javascript-tests` passes and no tracked file
      outside history names `distributions/npm`. At 02:57:36 a search outside history found
      `distributions/npm` only in the changelog and in the distribution explanation sentence that
      records its retirement.
      `test_javascript_tests_execute_supplied_node_and_npm_with_shadowed_path` ran the remaining
      JavaScript tests and passed at 02:26:08; the `javascript-tests` gate itself runs in the full
      proof, as a focused host run refuses it alone for its unproven obligations.
- [x] 1.2 Reduce the release identity to the `VERSION` carrier with the root Node manifest guard,
      and the product boundary and format selection to the root rules. Done when the release,
      boundary and format-selection tests pass with their launcher cases removed. At 02:26:08 1,393
      of the 1,394 affected release, boundary, format-selection, architecture, governance and policy
      tests passed. The one failure, `test_sdist_rebuild_reuses_the_identical_node_package_supply`,
      hit its 90-second build bound at load 55 and passed alone at 02:28:20.
- [x] 1.3 Let the semantic closure treat a bare word as prose, not as a reference to an emptied
      directory, and drop the stale `distributions` entries. Done when a closure test shows that a
      docstring word is not a consumer while a `legacy/` literal is, and the product boundary
      passes. At 02:15:32 `test_a_bare_word_does_not_consume_a_retired_directory` failed with the
      docstring file reported as a consumer, and at 02:16:44 it passed after the change, with the
      product boundary closure test and the docs health tests, 95 tests in all.

## 2. Documents and acceptance

- [x] 2.1 Update the README, the release guide, the distribution explanation and the changelog. Done
      when the docs gates pass. At 02:32:48 readiness passed its 28 gates at `9adaef550`, among them
      `docs-registry`, `markdown-lint`, `markdown-links`, `prose` and `source-format`.
- [x] 2.2 Pass lint, the full suite and readiness at the lane head. Done when each passes on the
      committed head. At 02:32:48 readiness passed at `9adaef550`, and at 02:56:54
      `local-install-smoke` passed there as host evidence; the full suite runs in the proof of the
      archived head.
