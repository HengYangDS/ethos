# Tasks

## 1. The next action

- [x] 1.1 Render the relock as `mise --cd <root> lock` with the adopted root. Done when
      `test_an_applied_pin_is_followed_by_the_relock` asserts the rooted form for a release build
      and passes, and the step's kind stays `instruction`. Seen failing with the bare form first;
      the file's 11 tests pass at `cf19d59b4`.
- [x] 1.2 State the rooted form in the adoption architecture page and the unreleased changelog
      entry. Done when both name `mise --cd <root> lock` and pass Prettier and Vale. Done in
      `cf19d59b4`.

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. The static pre-check and readiness passed at `ba9a1046d`, and the hosted runs of that
      head passed on both forges.
