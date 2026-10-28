# Tasks

## 1. Retention Selection Window

- [x] 1.1 Prove the window with a regression: a consumer whose selection lock is held keeps its
  record and its installation through retention, and a later retention after it selects the
  installation and the other consumer goes still retains it. Done when the test fails against
  `a6ad56b67` (the installation was removed while the pinning repository's `CURRENT` named it,
  and the lock was free while hook installation pinned:
  `build/evidence/retention-selection-window/red.log`).
- [x] 1.2 Make the selection lock one object per repository and read each consumer's selectors under
  a non-blocking acquisition of it in retention. Done when the host-retention, legacy-supply and
  selection tests pass (578 passed across the 25 test modules that import a changed module,
  `green.log`).
- [x] 1.3 Hold the selection lock from the pins through the selector writes in hook installation and
  adoption, with a regression that the lock is held while hook installation pins. Done when the
  activation, adoption and lane-start tests pass and `python_product` grows by at most 8 lines
  (`green.log`; `python_product` 69,994, +8).
- [x] 1.4 Record the fix under `[Unreleased]` in `CHANGELOG.md`. Done when `markdown_lint` and
  `prose` pass (both pass with the other fast gates on `b41ecb49d`).

## Workflow follow-up

- Archive this Change and prove the archived head once. After landing, hosted Windows host
  conformance passes twice on the landed head before a release Change refreshes the 0.2.0-alpha.18
  entry there.
