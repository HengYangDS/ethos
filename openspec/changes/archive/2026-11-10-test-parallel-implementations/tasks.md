# Tasks

## 1. One owner per test behavior

- [x] 1.1 Extend the parallel-implementation gate to `tests/` with decorator-aware test shapes. Done
      when the gate reports the 30 groups before the dedupe, none after it, and the planted case
      groups only identically decorated tests. RED: with only the gate change applied at b64fbb689,
      `test_no_behavior_is_implemented_twice` failed with 30 groups (first: the product and
      journey-test `_digest`); GREEN after the dedupe in 6bcda782c (6 passed with the
      decision-density tests); the planted case groups two identically decorated tests and keeps a
      differently parametrized one apart.
- [x] 1.2 Give each group one owner and delete its copies. Done when the touched tests pass and
      `python_tests` falls. Each group has one owner (6bcda782c, 5ab05f098); the impacted sweep at
      5ab05f098 passed 6,149 tests with 3 skipped; enforced `python_tests` 99,993 to 99,854 in the
      lane (-139), product +6, tools -5.

## 2. Acceptance

- [x] 2.1 Pass the precheck, the impacted sweep and readiness at the lane head. Done when each
      passes on the committed head. At 51817dcd2: the precheck passed with 0 findings, the impacted
      sweep (330 files) passed 6,149 tests with 3 skipped, local-install-smoke passed, and readiness
      passed 28 of 28 gates.
