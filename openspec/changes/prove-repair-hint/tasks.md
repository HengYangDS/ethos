# Tasks

## 1. Routing

- [x] 1.1 Route a repairable gap to the repair preview. Done when a report with a repairable gap
      names `ethos lane repair-paradigm --json`, a report with only judgment gaps names the first
      gap's repair, each test failed before the change, and the paradigm report and repair tests
      pass. Evidence: red at 10:48:07, before the implementation: `test_paradigm_next_action.py` and
      `test_paradigm_report.py` failed to import the routing function, 51 other tests passed. Green
      at 10:52:25 in `babe19eea`: 383 passed over the 17 test files that reach the paradigm report
      and repair, including `tests/unit/cli/land/test_readiness.py`, whose refused publish now names
      `ethos lane repair-paradigm --json`.

## 2. Acceptance

- [ ] 2.1 Pass readiness and the precheck at the lane head. Done when each passes on the committed
      head.
