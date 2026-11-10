# Tasks

## 1. One owner for decision density

- [x] 1.1 Add the complexipy test and its baseline. Done when the test fails with no baseline,
      passes with the measured one, refuses a planted function above 15 and a stale entry. RED: with
      an empty baseline the test failed naming 342 functions; GREEN with the measured 342-entry
      baseline in 6bc98359b (2 passed); the planted test refuses a nested function above 15 and
      names a stale pin, and 157b304e4 pins the keyword-argument score.
- [x] 1.2 Retire C901 and PLR0912 and select PLR0916. Done when Ruff passes with the new selection
      and `max-bool-expr = 23`. Ruff 0.17.4 passes at 6bc98359b with C901 and PLR0912 removed and
      PLR0916 at `max-bool-expr = 23`; probes at 22 and 5 report 1 and 67 conditions.
- [x] 1.3 Lock complexipy and bind the rebuilt CI supply image. Done when `uv lock --check` passes
      and the CI projection check reads the new image. `uv lock --check --offline` passes with
      complexipy 8.3.0; supply run 42802891581 built `sha256:5fbb5970` from 6bc98359b, bound in
      bbd139b13, and the supply currency and dual-forge projection tests pass (7 passed).

## 2. Acceptance

- [x] 2.1 Pass the precheck, the impacted tests and readiness at the lane head. Done when each
      passes on the committed head. At 51817dcd2: the precheck passed with 0 findings, the impacted
      sweep (330 files) passed 6,149 tests with 3 skipped, local-install-smoke passed, and readiness
      passed 28 of 28 gates.
