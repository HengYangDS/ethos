# Tasks

## 1. Failing evidence first

- [x] 1.1 Add `tests/architecture/test_single_test_runner.py`: in the default and full proof sets
      exactly one gate is a provider row of `ethos.adapters.gates.python_quality:behavior_report`,
      and no selected gate command, Nox session it runs or module that session imports by name has a
      `-m pytest` argv. Done when it fails at the lane's base on `unit-architecture`
      (`nox -s tests`) and on `architecture_projection` (`tools/ci/sessions.py:252-266`). (At the
      base both proof sets select no probe row, and the scan names `architecture-projection` and
      `unit-architecture`.)
- [x] 1.2 Add probe cases to `tests/unit/adoption/quality/test_python_native_configuration.py`: a
      fixture whose `.config/checks/pytest/pytest.toml` collects only `check_*` functions, and one
      whose `.config/checks/coverage/coverage.toml` declares `fail_under = 100` over a partly
      covered module. Done when, against the current probe, the first blocks with no case collected
      and the second passes, so both miss their new expectations. (Before the probe change the first
      blocked with `quality_behavior_pytest_empty` and the second passed at 77.78 percent.)
- [x] 1.3 Add probe cases for the bound and the reports in the same module: `timeout_seconds=1200`
      reaches `run_command` as 1200 through both providers and the default stays 600; with
      `ETHOS_NATIVE_OUTPUT_DIR` set, the attempt's `pytest/junit.xml`, `pytest/events.jsonl`,
      `coverage/coverage.xml` and the results the suite wrote appear there, and without it nothing
      remains outside scratch; the fixture's worktree gains no `__pycache__` or other untracked or
      ignored path. Done when they fail against the current probe. (Before the probe change the
      timeout cases failed with 600 and an unknown keyword, and the report cases blocked.)

## 2. The shipped probe applies native configuration

- [x] 2.1 Make the probe pass the paradigm pytest carrier with `--rootdir`, the coverage carrier
      with a bare `--cov`, the gate's `timeout_seconds` (through `code_quality.py` as well), the
      attempt's report root as `ETHOS_NATIVE_OUTPUT_DIR`, the copy to the runner's native output
      root, `PYTHONPYCACHEPREFIX` under the scratch, and scratch removal through
      `remove_owned_path`. Done when 1.2 and 1.3 pass and `tests/unit/adoption/quality` passes. (The
      eight probe cases pass, and 695 cases of the 27 modules that import either provider pass.)
- [x] 2.2 Add `-n auto --maxprocesses=12 --dist=load --maxschedchunk=1 --durations=20` to
      `.config/checks/pytest/pytest.toml` and replace `--strict-config --strict-markers` with
      `strict = true`. Done when collection under the file reports no error, after renaming any
      duplicate parametrization id, and `PYTEST_XDIST_AUTO_NUM_WORKERS=4` starts four workers. (Two
      duplicate-id parametrizations got explicit ids; 7,793 cases collected with no error; the
      variable started `4/4 workers`.)
- [x] 2.3 After refreshing the lane onto the landed `probe-supply` binding, run ETHOS's suite once
      through the probe with `timeout_seconds=7200` (a direct provider call in the lane, not a
      proof) and record in design.md's Context each refusal and each test that needs an executable
      outside the probe's locked PATH. Done when the observed gaps are listed. (The first run, at
      `5734e7dbe`, stopped after 205 cases on this Change's unfinished removals, design.md Context;
      it runs again after 5.4. The second, at `215af814b`, passed with one new skip outside the
      locked PATH, recorded there.)
- [x] 2.4 Point Hypothesis's native `HYPOTHESIS_STORAGE_DIRECTORY` at the attempt's scratch. Done
      when the probe case whose suite writes there leaves nothing outside scratch and no path in the
      fixture's worktree. (Before the change the suite's lookup failed and the probe blocked.)

## 3. ETHOS's runner values become native configuration

- [x] 3.1 Move the suite's process environment from `tools/ci/python_test_gate.py:383-402` into
      `tests/conftest.py`, write Allure results into the attempt's report root, and remove
      `ETHOS_NATIVE_OUTPUT_DIR` inside each case. Done when a case asserting these values inside a
      test passes through the probe, where it failed before the move. (Before the move the case
      failed with `KeyError: 'PYTHONDONTWRITEBYTECODE'` in the probe's environment.)
- [x] 3.2 Declare `fail_under = 95` in `.config/checks/coverage/coverage.toml`, delete
      `.config/checks/coverage/policy.toml`, and add the boundary regression: the declared floor is
      at least 95, and coverage's own comparison rejects 94.99 and accepts 95.00 at the declared
      precision. Done when the regression fails against `fail_under = 94` and passes against 95.
      (Against 94 both comparisons fail; against 95 the regression passes.)
- [x] 3.3 Move the retained runner cases (worker loss without replay, bounded failure, warm and
      empty failure history, tmp-path retention, bounded failure report) to
      `tests/architecture/test_pytest_configuration.py` against the configuration, and the two
      owned-removal cases to `tests/unit/adapters/repo/runtime/test_filesystem.py`. Done when they
      pass without importing `tools.ci`. (14 cases pass in the two modules; the worker-loss case
      runs two workers under the carrier.)
- [x] 3.4 Register and load the `proof` Hypothesis profile unless `--hypothesis-profile` selects
      another, and choose the tool cache as Hypothesis's storage only when
      `HYPOTHESIS_STORAGE_DIRECTORY` is absent (design Decision 14). Done when the two configuration
      cases pass with and without the variable. (Before, the profile was not registered and the
      storage ignored the variable.)

## 4. Report-only tier guard

- [x] 4.1 Add the guard's cases: a case under `tests/unit` that opens a file is recorded as
      exceeding its tier; a lazy import is not recorded; a loopback connection outside `tests/unit`
      is recorded without exceeding; the outcome is unchanged. Done when they fail without the
      guard. (`tests/architecture/test_tier_guard.py` runs a nested pytest; without the module it
      failed on the missing plugin.)
- [x] 4.2 Add `tests/support/tier_guard.py` and load it from `tests/conftest.py`. Done when 4.1
      passes and a full run's JUnit carries `ethos.crossed` and `ethos.exceeds` properties. (The
      second full run's JUnit carries them for 5,955 of its 7,764 cases.)
- [x] 4.3 Watch setup, call and teardown, record design Decision 7's event table, and leave out
      module loading, the test tools' own work, the report root and wider-scope fixture setups. Done
      when the nested guard cases pass. (Before, a fixture's setup and teardown, a rename, a removal
      and `os.system` went unrecorded, and Hypothesis's own reads were charged to the case; a read
      through `importlib.metadata` went unrecorded until only `importlib._bootstrap*` counted as
      module loading, committee round 12.)

## 5. One runner

- [ ] 5.1 Make `unit-architecture` a provider row (`python_quality:behavior_report`,
      `profile = "product-toolchain"`, `tool_adapter = "ethos"`, `timeout_seconds = 7200`) without
      native outputs, and remove `coverage-floor` from the registry and both proof sets. Done when
      1.1 passes and the gate passes in the lane.
- [ ] 5.2 Delete `tools/ci/python_test_gate.py`, `python_test_order.py` and
      `python_test_bytecode.py`; the `tests` and `coverage_floor` sessions and the pytest run in
      `architecture_projection`; `_pytest_runner_findings` and its carrier entry; `junit_report`;
      and the retired inputs in `system/surfaces.toml`. Done when `rg` finds none of these names
      outside archived Changes and the main specs this Change's deltas amend, and module layout,
      semantic closure and generated artifacts pass.
- [x] 5.3 Make hosted verification clear `build/evidence/quality/tests`, name it as the native
      output root, take test and coverage figures from the probe's evidence, refuse Allure results
      whose case identities differ from the execution's, and render the Allure views; rename
      `ETHOS_TEST_WORKERS` to `PYTEST_XDIST_AUTO_NUM_WORKERS` in `.config/ci/pipeline.cue` and
      regenerate both projections. Done when `tests/unit/ci/test_hosted_verification.py`, the
      re-targeted Allure cases and `tests/architecture/test_ci_provider_projections.py` pass. (They
      pass in the 49-module focused run; the render owner is public as `render_allure`.)
- [x] 5.4 Apply the case dispositions in design.md. Done when every removed case has its disposition
      there and no test imports a deleted module. (`rg -w` finds the deleted names only in archived
      Changes, the main specifications this Change amends, this Change and CHANGELOG's removal.)
- [x] 5.5 Add the no-retry regression, pinning existing behavior: a report log with a `rerun`
      outcome is refused. Done when it passes.
- [x] 5.6 Compare the node identities that the probe executes in the lane with those the parent
      tree's runner executed in the base proof (its JUnit, kept as
      `build/runtime/work/test-runner-unification/baseline/junit.xml`). Done when the difference is
      exactly the removed cases of design.md's dispositions and the cases this Change adds. (Against
      7,785 base identities the second run lacks 106 and adds 85: the removed and moved cases, the
      12 strict-id renames, the 44 parallel-proof renames and one hosted re-parametrization, each
      recorded in design.md;
      `build/runtime/work/test-runner-unification/lane/completeness-p2.json`.)
- [x] 5.7 Make the commit-trust material case bind its material under its own `tmp_path`, since
      `tempfile` reads `TMPDIR` once per process. Done when the case asserts that the selected
      anchor is under `tmp_path` and passes, where it failed before. (Before, the anchor was under
      the host's temporary root, and every run left one `ethos-ci-trust-*` directory there; design
      Context.)

## 6. Specifications and documents

- [ ] 6.1 Write the quality and repository-governance deltas. Done when strict OpenSpec validation
      passes and a simulated archive leaves every spec valid.
- [ ] 6.2 Update README.md's Development commands, `docs/reference/configuration.md`,
      `docs/architecture/generated-artifact-topology.md`, the removal target named in
      `docs/research/foundations/execution.md:38`, the terminal plan's coverage-policy link and
      CHANGELOG's `[Unreleased]`. Done when the documentation gates pass.

## 7. Measurement

- [ ] 7.1 Measure the distribution mode cold, `load --maxschedchunk=1` against `worksteal`, one run
      each, and keep the faster in `.config/checks/pytest/pytest.toml`. Done when both wall times
      and peak memory are recorded in design.md.
- [ ] 7.2 Measure the guard's overhead and the retired shared bytecode with one run without each,
      and count cases per tier from a full run's JUnit. Done when design.md records all three and
      states whether Decision 6's bytecode fallback applies.
- [ ] 7.3 Measure the budgets. Done when product is at most 70,000, tests at most 90,000 and every
      touched Python file at most 500 effective lines, with the values recorded.

## Workflow follow-up

- Archive, prove the archived head once, land, close out and publish; compare the proof's
  `unit-architecture` time with 895.1 s and confirm that both hosted planes upload JUnit, Cobertura
  and Allure.
- The canonical checkout's `build/evidence/quality/tests/` loses its local producer and consumer
  (173 orphaned coverage fragments at `4edfa8f43`, TI), so it is disposable residue once this Change
  lands; closeout removes that exact directory.
