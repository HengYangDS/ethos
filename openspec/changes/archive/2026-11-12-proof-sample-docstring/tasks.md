# Tasks

## 1. Sample package

- [x] 1.1 Open the sample package with a docstring. Done when the test fails for both parameters
      before the change and passes after it. Evidence: 3e27dfc9d opens the sample package with a
      docstring. The test failed for both parameters before it (01:06:13 to 01:06:26) and passed
      after it with the architecture suite (325 passed, 1 skipped, 01:07:59 to 01:09:37); Ruff's
      format check accepts both sample variants, and its isolated floor reports only the unused
      import.

## 2. Acceptance

- [x] 2.1 Pass readiness, the changed test file and the architecture suite at the lane head. Done
      when each passes on the committed head. Evidence: readiness passed 28 gates at 3e27dfc9d with
      the 6 heavy gates left to the proof (01:10:26 to 01:13:33), and the changed test file and the
      architecture suite passed with the committed change (325 passed, 1 skipped, 01:07:59 to
      01:09:37).
