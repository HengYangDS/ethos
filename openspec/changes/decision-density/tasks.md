# Tasks

## 1. One owner for decision density

- [ ] 1.1 Add the complexipy test and its baseline. Done when the test fails with no baseline,
      passes with the measured one, refuses a planted function above 15 and a stale entry.
- [ ] 1.2 Retire C901 and PLR0912 and select PLR0916. Done when Ruff passes with the new selection
      and `max-bool-expr = 23`.
- [ ] 1.3 Lock complexipy and bind the rebuilt CI supply image. Done when `uv lock --check` passes
      and the CI projection check reads the new image.

## 2. Acceptance

- [ ] 2.1 Pass the precheck, the impacted tests and readiness at the lane head. Done when each
      passes on the committed head.
