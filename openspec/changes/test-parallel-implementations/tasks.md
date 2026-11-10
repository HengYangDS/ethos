# Tasks

## 1. One owner per test behavior

- [ ] 1.1 Extend the parallel-implementation gate to `tests/` with decorator-aware test shapes.
      Done when the gate reports the 30 groups before the dedupe, none after it, and the planted
      case groups only identically decorated tests.
- [ ] 1.2 Give each group one owner and delete its copies. Done when the touched tests pass and
      `python_tests` falls.

## 2. Acceptance

- [ ] 2.1 Pass the precheck, the impacted sweep and readiness at the lane head. Done when each
      passes on the committed head.
