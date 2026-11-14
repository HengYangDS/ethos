# Tasks

## 1. The guard

- [x] 1.1 Add the four-case test to `tests/unit/lanes/hook/test_path_admission.py`. Done when its
      two removal cases fail on the unchanged guard and its edit and creation cases pass.
- [x] 1.2 Read the effect before the denied placement refuses in
      `src/ethos/adapters/admission/paths.py`. Done when the four cases pass and ruff and Ty pass.
- [x] 1.3 Observe the effect in one helper and lower the guard's pinned decision score. Done when
      `tests/architecture/test_decision_density.py` passes with `_check_path` pinned at 16.

## 2. Documents

- [x] 2.1 Add the Fixed line to the Unreleased section of `CHANGELOG.md`. Done when Prettier, Vale
      and codespell accept it.

## 3. Lane

- [x] 3.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Passed at `76510cd54`.

## Workflow follow-up

- The governed repository that reported the defect removes its ten scripts in the lane that binds
  the release carrying this Change; its own lane owns that removal.
