# Tasks

## 1. Rule

- [x] 1.1 Plant a narrower `default` whose closure holds a networked gate, and one that holds a
      package gate, together with a `default` equal to `full` that holds a networked gate. Done when
      the two narrower cases fail on the current validator and the equal case passes. From 08:39:45
      to 08:39:49 at `d8760f044`, the two planted narrower cases of
      `test_gate_registry_malformed_references_fail_closed` failed on the current validator, and
      `test_a_default_equal_to_full_may_hold_a_networked_gate` passed.
- [x] 1.2 Enforce the rule in `_validate_proof_sets`. Done when the planted cases refuse with the
      new message, the equal case passes and ETHOS's registry loads. With the rule in
      `_validate_proof_sets`, the registry tests passed 65 tests from 08:41:07 to 08:41:10: both
      narrower cases refuse with `default proof gate is not an offline source check`, the equal case
      passes, and ETHOS's registry loads (readiness ran 28 gates at `059799ea1`).
- [x] 1.3 Record the rule in `CHANGELOG.md` `[Unreleased]`. Done when a `### Changed` bullet names
      it. `CHANGELOG.md` `[Unreleased]` `### Changed` names the rule and the unaffected equal case,
      at `059799ea1`.

## 2. Acceptance

- [x] 2.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there. The precheck passed with 0 findings at 08:41:27 on the Change's tree. The
      impacted sweep of 294 test files passed 5598 tests with 2 skipped from 08:42:10 to 09:14:56 on
      that tree. Readiness passed 28 gates from 09:16:08 to 09:17:23 at `059799ea1`.
