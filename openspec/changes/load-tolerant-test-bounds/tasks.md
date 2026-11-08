# Tasks

## 1. Bounds

- [x] 1.1 Wait within the tool deadline. Done when `ready_descendant` and the workflow test use
      `seconds("tool")` and the tests that use them pass. Evidence: at 71dfe388b both waits use
      `seconds("tool")`; the two failing tests' modules `test_capture.py` and `test_workflow.py`
      passed (39 tests, run between 19:41:27 and 19:42:39), and every test that imports
      `tests.support.subprocesses` passed (350 tests, 19:43:22 to 19:49:52).

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: the precheck passed against a71c0900c (19:43) and readiness passed 28 gates at
      71dfe388b with the 6 heavy gates left to the proof (19:53:21).
