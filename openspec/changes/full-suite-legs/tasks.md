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

- [ ] 5.1 Apply the patch in the Work Lane and pass its pre-check, readiness and
      `ethos lane project --check`. Done when all three pass at the lane head.
- [ ] 5.2 Read the push run of the lane head. Done when the three suite jobs are skipped and
      `hosted checks` succeeds.
- [ ] 5.3 Dispatch the workflow on the lane's ref with `qualify_head` at its head. Done when the
      jobs `suite linux-x64 / Python 3.12` and `suite linux-x64 / Python 3.13` succeed, the log
      of each suite step begins with `Python 3.12.` and `Python 3.13.` and ends with pytest's
      summary line, each job's artifact holds a JUnit report and a coverage report, and
      `hosted checks` succeeds.
- [ ] 5.4 Read the job `suite windows-x64 / Python 3.14` of the same run. Done when its result
      is recorded with the step it ended in, and the run and `hosted checks` succeed whatever
      that result is.
- [ ] 5.5 Record each leg's duration beside the quality gates job's of the same run. Done when
      the three durations are written where the next editor of the model's timeout table reads
      them; they are the `suite` class's first samples.

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

## Workflow follow-up

- Delivery: read the first scheduled run after this Change reaches the default branch. It runs
  the three legs, and `hosted checks` needs the two Linux legs there too.
- Delivery: set the `suite` class's minutes by the method of the model's timeout table once its
  legs have the samples that the method asks for.
