# Tasks

## 1. The probe's leg mode

- [x] 1.1 Add `test_a_leg_runs_on_its_callers_interpreter_and_never_decides_the_floor` to
      `tests/unit/adoption/quality/test_python_native_configuration.py`. Done when both cases
      fail because the probe selects the locked interpreter, in a repository that declares Mise
      and a floor its tests do not meet.
- [x] 1.2 Add the `leg` keyword to `behavior_report` in
      `src/ethos/adapters/gates/python_quality.py`. Done when 1.1 passes: the command names the
      caller's interpreter, a passing leg below the floor passes without a floor in its coverage
      evidence, and a failing run blocks with `quality_behavior_tests_failed`.
- [x] 1.3 Name the caller's interpreter for every leg. Done when a leg in a project whose Python
      range excludes its interpreter fails its sync with the caller named; it ran on an
      interpreter of uv's choice before. The lock states the same range, and the test reads
      uv's own refusal of the interpreter.

## 2. The session

- [x] 2.1 Add `tests/unit/ci/test_suite_leg.py`. Done when both cases fail before the session
      exists.
- [x] 2.2 Add `suite_leg` to `tools/ci/sessions.py` and its public sessions. Done when 2.1
      passes: the probe is called as a leg with the named deadline and with the repository's
      Mise first on its path, the log names the interpreter, and a leg that does not pass fails
      the session.
- [x] 2.3 Open one deadline scope around the probe in `suite_leg`. Done when the session's test
      shows the probe running inside a scope of the named deadline.

## 3. The model and the generated workflow

- [x] 3.1 Add `tests/architecture/ci/test_suite_legs.py` and the two required legs to the
      aggregate's pin in `tests/architecture/test_ci_provider_projections.py`. Done when both
      fail on the unchanged workflow.
- [x] 3.2 Declare the three legs, the `suite` class and its gate in `.config/ci/pipeline.cue`.
      Done when the model compiles and is formatted, and does not compile with the class's
      minutes at the test gate's 120.
- [x] 3.3 Generate `.github/workflows/ci.yml` from the model. Done when the projection check
      passes, the second forge's pipeline is unchanged, and 3.1 passes.
- [x] 3.4 Declare the leg's setup margin in the model and refuse a suite job below the deadline
      plus the margin. Done when a regression compiles the model with the class's minutes at
      125 and reads the refusal of `timeout-setup:suite`, and the generated files are
      unchanged.

## 4. Documents and budgets

- [x] 4.1 State the legs in step 4 of the release guide and the leg's coverage in the
      configuration reference; add the changelog entry and the quality delta. Done when OpenSpec
      validates the Change strictly and Prettier and the documentation registry accept the
      documents.
- [x] 4.2 Measure the source budget. Done when the Change's commits are measured against their
      parents and stated by class: the integration adds 14.6 product, 108.0 tests and 23.7 tools
      line-equivalents, the tools all in `tools/ci/sessions.py`, and the four review repairs beside
      it add -0.4, 57.6 and 2.7 (14.1, 165.6 and 26.4 in all).

## 5. Lane, hosted run and owner

- [x] 5.1 Apply the patch in the Work Lane and pass its pre-check, readiness and
      `ethos lane project --check`. Done when all three pass at the lane head. All three passed at
      `4a5029e96` on 2026-11-17: the pre-check with 472 impacted test modules (9,555 passed, 5
      skipped, no finding), readiness with its 28 gates, and the projection check.
- [x] 5.2 Read the push run of the lane head. Done when the three suite jobs are skipped and
      `hosted checks` succeeds. Run 43991816712 at `4a5029e96`: the three suite jobs are skipped,
      the quality gates job passes its 34 gates, and `hosted checks` succeeds.
- [x] 5.3 Dispatch the workflow on the lane's ref with `qualify_head` at its head. Done when the
      jobs `suite linux-x64 / Python 3.12` and `suite linux-x64 / Python 3.13` succeed, the log of
      each suite step names `Python 3.12.` and `Python 3.13.` as the leg's interpreter and shows
      pytest's summary line, each job's artifact holds a JUnit report and a coverage report, and
      `hosted checks` succeeds. Run 43991840423 at `4a5029e96`: both jobs succeed, their steps name
      Python 3.12.16 and Python 3.13.18 and end with `9810 passed, 5 skipped`, each artifact holds
      `pytest/junit.xml` and `coverage/coverage.xml`, and `hosted checks` succeeds. The run of the
      head before it, 43978304848, failed the Python 3.12 leg on the defect of task 6.7.
- [x] 5.4 Read the job `suite windows-x64 / Python 3.14` of the same run. Done when its result is
      recorded with the step it ended in, and the run and `hosted checks` succeed whatever that
      result is. In run 43991840423 the job fails in its step
      `Repeat the suite on this leg and record its coverage`: pytest stops after 4 failures of 70
      tests, with 65 passed and 1 skipped. The run and `hosted checks` succeed.
- [x] 5.5 Record each leg's duration beside the quality gates job's of the same run. Done when the
      three durations are written where the next editor of the model's timeout table reads them;
      they are the `suite` class's first samples. Written in the comment of the model's timeout
      table, from run 43991840423: 38.0 minutes on Python 3.12, 35.9 on Python 3.13 and 13.0 on
      Windows to its failure, beside 38.7 for the quality gates job.

## 6. Findings of the first run

- [x] 6.1 Report a command's bound as its timeout on every interpreter, in
      `src/ethos/adapters/process.py`. Done when the regression fails without the change and
      the Python 3.12 leg passes `tests/unit/adapters/process/test_capture.py`.
- [x] 6.2 Change the runtime identity test's interpreter tag to one that the running
      interpreter does not hold. Done when the Python 3.13 leg passes
      `tests/unit/adapters/repo/runtime/test_selection.py`.
- [x] 6.3 Name a failed leg's diagnostics in the session's error. Done when the session's test
      reads them, and a leg that fails before pytest starts shows its cause in the job's log.
- [x] 6.4 Run the whole suite at Python 3.12 and at Python 3.13 without the stop at the first
      failure. Done when each failure is repaired in this Change or named with its owner.
- [x] 6.5 Compare the code subjects with the commit without naming them on a command line, in
      `src/ethos/adapters/repo/gate_policy.py`. Done when the regression fails without the
      change and the Windows leg's log shows pytest starting.
- [x] 6.6 Hand a tool its text input with the caller's line endings on every platform, in
      `src/ethos/adapters/process.py`. Done when the regression fails without the change and
      the Windows leg passes `tests/architecture/ci/test_job_identity.py`.
- [x] 6.7 Read a command line that names no file as no writer on every interpreter, in
      `src/ethos/adapters/store/retention/writers.py`. Done when the regression fails without the
      change at Python 3.12 and at Python 3.13, and the Python 3.12 leg passes
      `tests/unit/cli/test_hook_record_retirement.py`. Without the change 17 tests of the module's
      importers fail at Python 3.12 and at 3.13; with it all pass at 3.12, 3.13 and 3.14, and both
      Linux legs of run 43991840423 pass the named module.

## Workflow follow-up

- Delivery: read the first scheduled run after this Change reaches the default branch. It runs
  the three legs, and `hosted checks` needs the two Linux legs there too.
- Delivery: set the `suite` class's minutes by the method of the model's timeout table once its
  legs have the samples that the method asks for.
- Windows leg: of its four failures one is diagnosed, a test that starts `bash`, which is the WSL
  launcher on the runner. Three are crashes of a test worker in
  `tests/architecture/ci/test_supply_image_currency.py` and
  `tests/architecture/test_ci_provider_projections.py`, without a diagnosis. Read again at the cut
  of 0.2.0-beta.13.
