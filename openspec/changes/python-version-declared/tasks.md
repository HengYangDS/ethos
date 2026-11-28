# Tasks

## 1. Each repository declares its own Python version

- [x] 1.1 Narrow the paradigm: the Python module reads `project.requires-python` and admits any one
      `>=` clause naming a version; the Ruff row keeps `line-length = 100` and declares
      `target-version`, repaired with `py312` only while absent. Done when
      `test_a_repository_declares_its_own_python_version` passes at 3.11 and 3.14 and every
      paradigm case that passed on `cdb51d469` still passes.
      (`test_a_repository_declares_its_own_python_version` passes for `>=3.11` and `>=3.14`, and the
      21 paradigm test modules pass, 566 cases, at `0ec07e9e2`.)
- [x] 1.2 Render a Python file at the repository carrier's target only after the shipped and the
      repository's settings rendered it differently. Done when
      `test_the_carrier_target_settles_a_render_only_the_shipped_target_disagrees_on` passes in both
      forms and its `carrier-target` form fails without the second run.
      (The test passes in its `carrier-target`, `unfollowed-extend` and `other-setting` forms at
      `0ec07e9e2`; with the retry's second run removed, the `carrier-target` form fails.)

## 2. Acceptance

- [x] 2.1 Record the change in the changelog under Unreleased.
      (Under Changed in the unreleased section of the changelog.)
- [x] 2.2 Pass readiness and hand the full proof to the landing. Done when readiness passes and the
      Workflow follow-up states that the full proof runs on the archived head.
      (Readiness passed at `1af6179e5`; the Workflow follow-up below states the proof. The lane's
      full pre-check at `cb73eee88` failed only on the stale supply image that the next commit
      rebound, and left no pass.)

## Workflow follow-up

- Landing: the full proof runs on the archived head, and its receipt is the landing's. The hosted
  runs of that head are read before the landing.
