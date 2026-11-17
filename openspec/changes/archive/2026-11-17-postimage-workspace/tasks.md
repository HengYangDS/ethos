# Tasks

## 1. The regression and the repair

- [x] 1.1 Add a regression to `tests/unit/admission/test_patch_admission_public_fail_closed.py`
      that places Python's temporary directory inside another repository and admits a patch with
      an undeclared executable. Done when it fails on the unchanged module with a verdict of
      `pass`.
- [x] 1.2 Make the workspace a repository of its own, in the workspace's own module
      `src/ethos/adapters/admission/patch_workspace.py`. Done when 1.1 passes, also with a
      path-list separator in the temporary directory's name, the owner's tests read four
      shapes of patch in three places, and the six admission modules pass with the temporary
      directory inside a work tree and outside one.
- [x] 1.3 Refuse a patch that declares another kind of entry than a regular file. Done when a
      patch that declares a link and one that declares a submodule entry are refused by the
      owner's tests.

## 2. Documents and budgets

- [x] 2.1 Add the changelog entry and the governance delta. Done when OpenSpec validates the
      Change strictly and Prettier and the documentation registry accept the documents.
- [x] 2.2 Measure the source budget. Done when the report states product and tests.

## 3. The class and the lane

- [x] 3.1 Run the whole suite once with the temporary directory inside a work tree. Done when each
      failure is repaired in this Change or is named in the draft `gate-environment` with its owner.
      Run at `a725a9d6f` on 2026-11-17: 9,791 passed and 17 failed. The 17 start a pytest of their
      own and failed on the run's own option for the base directory; they pass with the temporary
      directory inside the work tree when the outer pytest alone receives that option. No failure is
      owed to the directory's place, so none is repaired or named.
- [x] 3.2 Pass the model review of this Change's code, then the pre-check and readiness at the lane
      head. Done when the review's triage is beside its record and both checks pass. The review read
      this Change's code in sixteen parts and ended at `a725a9d6f` with no comment, each part's
      triage beside its record; the pre-check and readiness passed at `4a5029e96` on 2026-11-17.

## Workflow follow-up

- Release: the release Change of 0.2.0-beta.12 names this repair under Fixed, with the releases
  that held the defect.
