# Tasks

## 1. Package docstrings

- [x] 1.1 Report a package marker without a docstring in the paradigm and refuse it in `pre-commit`,
      with the Breaking line. Done when an empty or docstring-less marker is reported and refused, a
      marker with a docstring passes, and ETHOS has no gap. Evidence: 29d1901fd adds
      `repository/paradigm/packages.py`, joins it to the paradigm report and `pre-commit`, and adds
      the Breaking line. The unit test could not import the module before the change (23:24:16 to
      23:24:22) and its six markers passed after it (23:25:13 to 23:25:21 with the report, hook and
      density tests, 90 passed; again 23:26:16 to 23:26:26); the in-lane function found no gap in
      ETHOS's 97 markers.

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: the precheck passed against 9ebeae1c8 with 0 findings (23:45:28 to 23:45:48),
      and readiness passed 28 gates at 9ebeae1c8 with the 6 heavy gates left to the proof (23:45:48
      to 23:47:58).
