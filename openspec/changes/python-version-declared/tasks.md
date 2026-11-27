# Tasks

## 1. Each repository declares its own Python version

- [ ] 1.1 Narrow the paradigm: the Python module reads `project.requires-python` and admits any one
      `>=` clause naming a version; the Ruff row keeps `line-length = 100` and declares
      `target-version`, repaired with `py312` only while absent. Done when
      `test_a_repository_declares_its_own_python_version` passes at 3.11 and 3.14 and every
      paradigm case that passed on `cdb51d469` still passes.
- [ ] 1.2 Render a Python file at the repository carrier's target only after the shipped and the
      repository's settings rendered it differently. Done when
      `test_the_carrier_target_settles_a_render_only_the_shipped_target_disagrees_on` passes in both
      forms and its `carrier-target` form fails without the second run.

## 2. Acceptance

- [ ] 2.1 Record the change in the changelog under Unreleased.
- [ ] 2.2 Pass the lane's pre-check and readiness, then the full proof.
