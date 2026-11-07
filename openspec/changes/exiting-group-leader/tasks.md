# Tasks

## 1. Process owner

- [x] 1.1 Wait within the reaping grace for a refused leader that still reports running, with the
      Darwin refusal tests in their own module. Done when a test shows that a leader exiting after
      the first refusal leaves cleanup clean, and the lasting-refusal tests still fail cleanup. At
      04:20:37 `test_a_leader_still_exiting_when_refused_is_not_a_survivor` failed with the
      PermissionError of row 26, and at 04:24:06 it passed with the 52 process tests, the
      lasting-refusal tests still failing cleanup as survivors.

## 2. Test bounds

- [x] 2.1 Choose the damaged blob deterministically with a diagnostic, and bound the sdist build by
      300 seconds. Done when both tests pass. At 04:23:09 the gate policy, version identity and
      process test files passed, 98 tests.

## 3. Acceptance

- [ ] 3.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
