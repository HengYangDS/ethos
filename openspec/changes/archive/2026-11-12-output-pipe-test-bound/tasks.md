# Tasks

## 1. Load-tolerant bound

- [x] 1.1 Wait for the subprocess for the shared tool deadline. Done when the test and the
      architecture suite pass. Evidence: 2249ff45f waits for the subprocess for `seconds("tool")`.
      Proof b10p5 failed only this test under a host load of 85 to 94 (1 failed, 9,159 passed,
      02:49:22 to 03:44:25); with the change the test and the architecture suite passed (312 passed,
      1 skipped, 03:47:34 to 03:48:36), and Ruff passed.

## 2. Acceptance

- [x] 2.1 Pass readiness at the lane head. Done when it passes on the committed head. Evidence:
      readiness passed 28 gates at 2249ff45f with the 6 heavy gates left to the proof (03:49:29 to
      03:52:02).
