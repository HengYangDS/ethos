# Tasks

## 1. A load-independent timeout fixture

- [x] 1.1 Move the timeout variant's sentinel ahead of pytest and Ruff. Done when, with the budget
      cut below the old critical path, the old fixture fails on the missing sentinel and the new one
      passes, and the committed fixture passes the Nox test module with its 15-second budget.
      Evidence: on the tree that 0a168a177 commits, the behavior session writes `behavior.xml`,
      prints the sentinel and sleeps before pytest. With the budget cut to 1 second, the old fixture
      failed 3 of 3 runs on `assert 'timeout-sentinel' in ''` (17:28:45 to 17:28:55, 17:30:58 to
      17:31:05, 17:31:05 to 17:31:12) and passed at 2 seconds (17:29:42 to 17:29:49) and 3 seconds
      (17:28:18 to 17:28:28); the new fixture passed 3 of 3 runs at 1 second (17:35:08 to 17:35:31).
      The 10 test modules that use the fixture passed with its 15-second budget (309 passed,
      17:31:35 to 17:33:55).

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: the precheck passed against 5eb47348b with 0 findings (17:52:28 to 17:52:35),
      and readiness passed 28 gates at 5eb47348b with the 6 heavy gates left to the proof (17:52:35
      to 17:54:36).
