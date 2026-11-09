# Tasks

## 1. Probe

- [x] 1.1 Bound the predecessor probe by the gate deadline. Done when the `slow` case of
      `test_predecessor_policy_probe_preserves_failure_identity`, a predecessor slower than the tool
      deadline, fails before the change and passes after it. Evidence: the `slow` case failed before
      the change (1 failed, 30 passed, 09:30:05 to 09:32:44, uncommitted on a8bcd4e8b) and passes
      after it (31 passed, 09:33:06 to 09:34:30); the impacted sweep at a7bbbef8d passed (359 files:
      6,988 passed and 2 skipped, 09:50:47 to 10:30:24).

## 2. Acceptance

- [x] 2.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there. Evidence: at a7bbbef8d the static precheck passed with no finding over 41
      changed files (09:51:36 to 09:51:42), readiness passed 28 gates (09:49:09 to 09:50:00) and the
      impacted sweep at a7bbbef8d passed (359 files: 6,988 passed and 2 skipped, 09:50:47 to
      10:30:24).
