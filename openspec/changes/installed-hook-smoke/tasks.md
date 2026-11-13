# Tasks

## 1. Installed hook step

- [x] 1.1 Add the step and its unit test. Done when the test fails before the step exists and passes
      after it, and a stand-in hook that refuses every commit, as the runtime of `21fbc6034` did,
      makes the step fail. Evidence: red at 19:09:38 in the lane, before the code:
      `test_product_hook.py` failed to import its module. Green at 19:12:43 in `335a9432f`:
      `tests/unit/ci/delivery/` with `tests/architecture`, 496 passed and 1 skipped by design; the
      test's stand-in hooks show that a hook refusing every commit, as the runtime of `21fbc6034`
      did, and one admitting every commit both fail the step.
- [x] 1.2 Pass `local-install-smoke` on the lane head. Done when its receipt records the admitted
      and the refused case. Evidence: `local-install-smoke` ran on the lane head `83479ede3` as host
      evidence from 19:15:19 to 19:27:39 and passed; its receipt
      `build/evidence/local-install/smoke.json` records `qualification.product_hook` as passed, the
      conforming edit admitted and the blank-led `.gitignore` refused with
      `pre_commit_text_layout:.gitignore:1`.

## 2. Acceptance

- [ ] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head, with tools at most 98 and tests at most 80 line-equivalents above the lane base.
