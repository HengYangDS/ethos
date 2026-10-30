# Tasks

## 1. Remove unreachable product code

- [x] 1.1 Remove the nine functions of design decision 1 that only their own tests call, with
      `_set_values`, `_values`, `CelRule`, `CelGapGroup` and `evaluate_cel_value`, and delete the
      tests that exercise only them. Done when none of these names occurs in `src/`, `tests/` or
      `tools/`. (None of the 21 removed names occurs there.)
- [x] 1.2 Remove the seven functions whose behavior a live owner holds, and give `_remove_tree` the
      public name of its one-line wrapper `remove_untracked_tree`. Move each case that only a
      removed function covered to the live owner's tests. Done when the test modules of every
      touched module pass. (The 109 test modules that import a touched module and the
      architecture suite pass: 2735 tests, 1 skipped.)

## 2. Verification

- [x] 2.1 Measure the lane head. Done when the source-budget measurement reports `python_product`
      within 70,000 and `adapters/repo/git.py` at most 500 effective lines. (`python_product`
      69,862, `python_tests` 89,520; `git.py` 473.)

## Workflow follow-up

- Archive this Change with the lane's other Changes and prove the archived head once.
- After the lane lands, propose the Change that decides the two specifications of design
  decision 3; review on 2026-11-02.
