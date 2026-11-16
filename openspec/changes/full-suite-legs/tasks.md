# Tasks

## 1. The probe's leg mode

- [ ] 1.1 Add `test_a_leg_runs_on_its_callers_interpreter_and_never_decides_the_floor` to
      `tests/unit/adoption/quality/test_python_native_configuration.py`. Done when both cases
      fail because the probe selects the locked interpreter, in a repository that declares Mise
      and a floor its tests do not meet.
- [ ] 1.2 Add the `leg` keyword to `behavior_report` in
      `src/ethos/adapters/gates/python_quality.py`. Done when 1.1 passes: the command names the
      caller's interpreter, a passing leg below the floor passes without a floor in its coverage
      evidence, and a failing run blocks with `quality_behavior_tests_failed`.
- [ ] 1.3 Name the caller's interpreter for every leg. Done when a leg in a project whose Python
      range excludes its interpreter fails its sync with the caller named; it ran on an
      interpreter of uv's choice before. The lock states the same range, and the test reads
      uv's own refusal of the interpreter.

## 2. The session

- [ ] 2.1 Add `tests/unit/ci/test_suite_leg.py`. Done when both cases fail before the session
      exists.
- [ ] 2.2 Add `suite_leg` to `tools/ci/sessions.py` and its public sessions. Done when 2.1
      passes: the probe is called as a leg with the named deadline and with the repository's
      Mise first on its path, the log names the interpreter, and a leg that does not pass fails
      the session.
- [ ] 2.3 Open one deadline scope around the probe in `suite_leg`. Done when the session's test
      shows the probe running inside a scope of the named deadline.

## 3. The model and the generated workflow

- [ ] 3.1 Add `tests/architecture/ci/test_suite_legs.py` and the two required legs to the
      aggregate's pin in `tests/architecture/test_ci_provider_projections.py`. Done when both
      fail on the unchanged workflow.
- [ ] 3.2 Declare the three legs, the `suite` class and its gate in `.config/ci/pipeline.cue`.
      Done when the model compiles and is formatted, and does not compile with the class's
      minutes at the test gate's 120.
- [ ] 3.3 Generate `.github/workflows/ci.yml` from the model. Done when the projection check
      passes, the second forge's pipeline is unchanged, and 3.1 passes.
- [ ] 3.4 Declare the leg's setup margin in the model and refuse a suite job below the deadline
      plus the margin. Done when a regression compiles the model with the class's minutes at
      125 and reads the refusal of `timeout-setup:suite`, and the generated files are
      unchanged.

## 4. Documents and budgets

- [ ] 4.1 State the legs in step 4 of the release guide and the leg's coverage in the
      configuration reference; add the changelog entry and the quality delta. Done when OpenSpec
      validates the Change strictly and Prettier and the documentation registry accept the
      documents.
- [ ] 4.2 Measure the source budget. Done when the report states product, tests and tools, with
      tools by file.

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

## Workflow follow-up

- Delivery: read the first scheduled run after this Change reaches the default branch. It runs
  the three legs, and `hosted checks` needs the two Linux legs there too.
- Delivery: set the `suite` class's minutes by the method of the model's timeout table once its
  legs have the samples that the method asks for.
