# Tasks

## 1. Behavior evidence

- [x] 1.1 Classify a run whose tests pass below the declared floor as
      `quality_behavior_coverage_below_floor` and record the floor. Done when the carrier test with
      a floor of 100 reports the new gap with the floor, a rounding test agrees with coverage.py's
      decision at the boundary, and the existing failing-test cases still report
      `quality_behavior_tests_failed`. At 01:29:42 the 77 tests of the two edited modules passed:
      the carrier test with a floor of 100 reports `quality_behavior_coverage_below_floor` with
      `{"fail_under": 100.0, "precision": 0}` where it reported `quality_behavior_tests_failed`
      before the change, and the six boundary cases of
      `test_a_floor_is_decided_as_coverage_decides_it` agree with coverage.py's rule. At 01:50:37
      the precheck passed with 1,528 tests in the 70 impacted files, failing-test cases included.

## 2. Acceptance

- [ ] 2.1 Pass lint, the quality tests and readiness at the lane head. Done when each passes on the
      committed head.
