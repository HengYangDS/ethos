# Tasks

## 1. The regression and the repair

- [ ] 1.1 Add a regression to `tests/unit/admission/test_patch_admission_public_fail_closed.py`
      that places Python's temporary directory inside another repository and admits a patch with
      an undeclared executable. Done when it fails on the unchanged module with a verdict of
      `pass`.
- [ ] 1.2 Run the workspace's apply under a ceiling at the workspace's parent in
      `src/ethos/adapters/admission/patch_admission.py`. Done when 1.1 passes and the six
      admission modules pass with the temporary directory inside a work tree and outside one.

## 2. Documents and budgets

- [ ] 2.1 Add the changelog entry and the governance delta. Done when OpenSpec validates the
      Change strictly and Prettier and the documentation registry accept the documents.
- [ ] 2.2 Measure the source budget. Done when the report states product and tests.

## 3. The class and the lane

- [ ] 3.1 Run the whole suite once with the temporary directory inside a work tree. Done when
      each failure is repaired in this Change or is named in the draft `gate-environment` with
      its owner.
- [ ] 3.2 Pass the model review of this Change's code, then the pre-check and readiness at the
      lane head. Done when the review's triage is beside its record and both checks pass.

## Workflow follow-up

- Release: the release Change of 0.2.0-beta.12 names this repair under Fixed, with the releases
  that held the defect.
