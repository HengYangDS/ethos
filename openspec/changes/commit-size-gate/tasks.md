# Tasks

## 1. Commit-time ceiling

- [ ] 1.1 Extract the shared measure and add the hook's staged check. Done when a test shows that
      `pre-commit` refuses a staged file over the ceiling with its lines and the ceiling, admits a
      commit whose worktree copy alone exceeds it, measures no symlink or gitlink, and the paradigm
      report's tests still pass.

## 2. Acceptance

- [ ] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
