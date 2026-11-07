# Tasks

## 1. Commit-time ceiling

- [x] 1.1 Extract the shared measure and add the hook's staged check. Done when a test shows that
      `pre-commit` refuses a staged file over the ceiling with its lines and the ceiling, admits a
      commit whose worktree copy alone exceeds it, measures no symlink or gitlink, and the paradigm
      report's tests still pass. At 05:47:24 the over, lexed and bound-ceiling cases failed because
      `pre-commit` admitted them; at 05:48:52 the symlink and gitlink cases failed while their
      objects were measured; at 05:49:06 the eight staged-size tests passed, and at 05:52:38 the 440
      hook and paradigm tests, including the paradigm report's size cases, passed.

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. The precheck's 239 impacted test files passed at 06:16:30, 5,046 tests with 2 skipped,
      and its static checks passed with no findings on the lines this Change adds; readiness passed
      its 28 gates at `e22574377` at 06:19:07.
