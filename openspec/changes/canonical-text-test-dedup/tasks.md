# Tasks

## 1. Duplicate helper

- [x] 1.1 Replace the canonical-text test's `_command` copy with the shared `run_ethos` helper. Done
      when `test_no_behavior_is_implemented_twice` fails before the change and passes after it, and
      the source-format tests pass. Evidence: 679ff0a5e replaces the canonical-text test's
      `_command` copy with `run_ethos`. `test_no_behavior_is_implemented_twice` failed before it
      (00:21:03 to 00:21:16, 1 failed, 3 passed) and passed after it with the architecture suite and
      the source-format tests (347 passed, 1 skipped, 00:21:40 to 00:23:09); Ruff and ty passed.

## 2. Acceptance

- [x] 2.1 Pass readiness and the precheck at the lane head. Done when each passes on the committed
      head. Evidence: readiness passed 28 gates at 679ff0a5e with the 6 heavy gates left to the
      proof (00:24:15 to 00:26:38). The precheck at 679ff0a5e passed its static checks and 5,952 of
      the 5,954 impacted tests, 3 skipped (314 targets, 00:27:12 to 01:01:00), and its coverage run
      passed 921 tests at 95 percent (01:01:01 to 01:04:31); `proof-sample-docstring` repairs the 2
      failures, and readiness passed 28 gates again at 3e27dfc9d (01:10:26 to 01:13:33).
