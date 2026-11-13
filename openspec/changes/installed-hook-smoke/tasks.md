# Tasks

## 1. Installed hook step

- [ ] 1.1 Add the step and its unit test. Done when the test fails before the step exists and passes
      after it, and a stand-in hook that refuses every commit, as the runtime of `21fbc6034` did,
      makes the step fail.
- [ ] 1.2 Pass `local-install-smoke` on the lane head. Done when its receipt records the admitted
      and the refused case.

## 2. Acceptance

- [ ] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head, with tools at most 98 and tests at most 80 line-equivalents above the lane base.
