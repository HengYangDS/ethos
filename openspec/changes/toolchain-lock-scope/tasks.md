# Tasks

## 1. One rule for the mise lock

- [x] 1.1 Move the task-only rule into `selects_tools` and make the paradigm report the lock only
      for a configuration that selects a tool. Done when the new task-only case fails before the
      change and passes after it, and the paradigm, mise and quality tests pass. Evidence: 12c94ed56
      adds `selects_tools` to `repository/paradigm/toolchain.py`; the paradigm's lock gap and the
      gates' `repository_mise_files` both read it. `test_a_task_only_mise_owner_needs_no_lock`
      failed before the change while the other 8 toolchain cases passed (20:10:55 to 20:11:02), and
      all 9 passed after it; the 31 paradigm, mise and quality targets passed (839 passed, 20:12:38
      to 20:14:31).
- [x] 1.2 Add the Changed line to `CHANGELOG.md`. Done when Prettier and Vale accept it. Evidence:
      12c94ed56 adds the Changed line; Prettier and Vale accepted it in the commit's checks.

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: the precheck passed against c9d5ebf22 with 0 findings (20:43:23 to 20:43:32),
      and readiness passed 28 gates at c9d5ebf22 with the 6 heavy gates left to the proof (20:44:02
      to 20:46:11).
