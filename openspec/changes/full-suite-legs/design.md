# Design

## Context

See the [proposal](proposal.md) and the [quality delta](specs/quality/spec.md). The pipelines are
one CUE model, `.config/ci/pipeline.cue`, from which the workflow of one forge and the pipeline of
the other are generated; neither generated file is edited by hand.

Read in this tree on 2026-11-15:

- The test gate `unit-architecture` runs the suite through the provider
  `ethos.adapters.gates.python_quality:behavior_report` and declares `timeout_seconds = 7200`
  (`system/repository-gates.toml`).
- Where the repository declares Mise, the probe pins the locked interpreter
  (`_locked_uv` in `src/ethos/adapters/gates/python_quality.py`), which is Python 3.14.10
  (`.config/mise/config.toml:8`). The project admits `>=3.12,<3.15` (`pyproject.toml:6`).
- The coverage carrier declares `fail_under = 95` (`.config/checks/coverage/coverage.toml:9`).
- The quality gates job runs on the Linux arm64 runner with Python 3.14, and a batch-head
  qualification runs ten host conformance legs (the generated workflow, read with a YAML parser).
- The workflow has 10 jobs and 527 lines before this Change, and 13 jobs and 686 lines after it.

Not measured: the duration of a suite leg. No leg has run. The archived `ci-economy` Change read
about 38 minutes for the quality gates job on the Linux arm64 runner; that figure is not a leg's.

## Goals / Non-Goals

Goals:

- The suite runs once for a release on Linux x64 at Python 3.12 and 3.13, and a failure there
  fails the check that the release guide requires before the tag.
- The Windows x64 suite runs at Python 3.14, is read for its result and its time, and blocks
  nothing.
- A leg records coverage. The floor keeps one decision for a proof attempt.
- A push and a pull request run the jobs they ran before.

Non-Goals:

- The release rehearsal, its `rehearsal-suite` job and its receipt, which the plan gives to its
  Change 6. That Change moves or reuses these legs.
- Triage of the Windows suite and a Windows journey, which DR-0021 places after 0.2.0.
- A shorter suite, shards, or any change to the second forge's pipeline.

## Decisions

1. **The legs run for a batch-head qualification and for the drift schedule.**
   - **Rests on:** appendix B.2 of the `rc-plan` design, which lets the Linux x64 legs block the
     tag; step 4 of the release guide, which requires the qualification's `hosted checks` before
     the tag; the model's `fullRun` condition, which already selects the full host conformance
     tier for the same two events.
   - **Considered:** a leg on every push, which adds three suite runs to the run that
     `ci-economy` shortened; waiting for the release rehearsal, which leaves this batch's tag
     without a blocking leg; the qualification alone, which saves three jobs a week and shows a
     drift at Python 3.12 or 3.13 only at the next batch head.
   - **Chosen because:** the qualification is the run that the release lane's owner reads before
     a tag, and one condition for "every tier" is easier to hold than two. The cost is three
     more jobs in each qualification and in each scheduled run.
   - **Applies to:** the workflow of the forge that runs the full gate set for a published ref.
     The second forge's runner is Linux arm64 at the locked Python, the combination that the
     quality gates job already covers, so its pipeline gains nothing.
2. **Each leg is its own job, and the aggregate needs the required ones.**
   - **Rests on:** the `ci-economy` design, which found that the forge's reference does not state
     the result of a job that fails under its own tolerance, and therefore keeps every tolerated
     job out of the aggregate's needs; `requiredJobs`, the one table that each job's condition
     and the aggregate's expectation read.
   - **Considered:** one matrix job with a tolerance for each leg, whose single result the
     aggregate would have to read with the Windows leg inside it; a matrix for the Linux legs and
     a job for Windows, which gives one list two shapes.
   - **Chosen because:** the aggregate then needs exactly the legs that block and never reads the
     Windows leg. A required leg joins `requiredJobs` under the full-run condition, so a push
     expects it skipped and a qualification expects it successful.
   - **Applies to:** the jobs `suite linux-x64 / Python 3.12`, `suite linux-x64 / Python 3.13`
     and `suite windows-x64 / Python 3.14`. Each name is fixed text and the leg's coordinates.
     The ruleset's required check, `hosted checks`, keeps its name.
3. **A leg is a mode of the shipped probe.**
   - **Rests on:** the requirement `ETHOS proves its Python suite through the probe it ships`;
     the pin read above; `test_a_leg_runs_on_its_callers_interpreter_and_never_decides_the_floor`,
     which fails without the mode because the locked interpreter is selected.
   - **Considered:** a session that builds its own pytest command, which is a second runner; an
     environment variable that the probe reads, which is an input no caller declares and every
     adopter's gate would inherit; a Mise declaration for each leg, which changes the locked
     supply.
   - **Chosen because:** one keyword on `behavior_report` selects the caller's interpreter under
     the rule the probe already applies to a repository without Mise. The gate runner passes a
     provider its arguments by name and never passes this one, so no gate becomes a leg.
   - **Applies to:** the Python provider. Its consumers are the provider row of the test gate,
     the code provider that adopters' gates use, hosted verification, which reads the provider's
     report from the proof, and the new session; only the session passes the keyword.
4. **A leg measures coverage with a floor of zero and never names the floor.**
   - **Rests on:** the carrier's floor read above; pytest-cov 7.1.0, where a floor given on the
     command line replaces the carrier's and a floor of zero fails no run (`plugin.py` in the
     locked environment); the requirement `A coverage shortfall names itself`.
   - **Considered:** a second carrier without the floor, which is two carriers to keep equal;
     a leg without coverage, which records less than appendix B.2 asks; the floor on the Linux
     legs, where a branch that one platform does not take would fail a leg on coverage alone.
   - **Chosen because:** the measuring run stays the same in every other respect. A leg whose run
     fails names its tests, because it decided no floor.
   - **Applies to:** the floor only. The probe's two other judgments of the measurement stay for
     a leg: a product file that no test executes, and a product file missing from the report.
5. **The test gate's declaration bounds a leg.**
   - **Rests on:** the gate's timeout read above; the model's `classGates` check, which refuses
     a job class whose minutes do not exceed a gate it runs.
   - **Considered:** a session that reads the registry itself, which puts the gate's name in a
     tool and leaves the job's timeout unchecked; a number of the model's own.
   - **Chosen because:** the model reads the gate's timeout from the registry it already
     receives, passes it to the session, and lists the gate for the `suite` class, so a longer
     gate timeout fails compilation instead of stopping a leg from outside.
   - **Applies to:** the `suite` class, set to the full set's 130 minutes. It has no sample, like
     the model's other provisional classes.
6. **A leg's record is the probe's reports.**
   - **Rests on:** the probe, which copies an attempt's JUnit report and coverage report to the
     native output root that its caller names; the rehearsal receipt of appendix B.1, which wants
     each leg's verdict, counts, coverage, skips and time.
   - **Considered:** a record file that the session writes, which is a second format for facts
     the two reports and the job's result already hold.
   - **Chosen because:** the session then adds no format. Its log names the interpreter, which
     neither report does, and shows how the run ended.
   - **Applies to:** the reports of a run that reached pytest. A leg that stops earlier uploads
     nothing, and its upload step fails with it.
7. **A leg is supplied as host conformance is, then as the quality gates job is.**
   - **Rests on:** `githubHostSupplyAt`, the supply order that host conformance runs on every
     hosted operating system and Python version; the quality gates job, whose bootstrap names
     Python 3.14 and has run on Linux only, and whose session prepares the scanner, budget, SBOM
     and prose tools and starts the proof with that supply, Mise included, on its path (`_prove`
     in `tools/ci/hosted_verification.py`); `mise_executable`, through which the probe finds Mise
     on the path alone.
   - **Considered:** the quality gates job's bootstrap with a Python parameter, whose order has
     not run on Windows; the whole prepared supply on the session's path, which the tests never
     read, because the probe gives them its own locked path.
   - **Chosen because:** after the host supply a leg takes the three preparations that the
     quality gates job's suite runs with: the four tools, the fixture supply and the commit
     trust. The session then puts the repository's own Mise first on its path, which is all the
     probe needs from it; a hosted job keeps that Mise in the tool cache.
   - **Applies to:** the three legs. Each prepares its tools in its own job. In today's workflow
     the prose tool and the inventory tool are prepared on every hosted platform, the commit
     trust is bound on Linux, macOS and Windows runners, and the fixture supply runs on Linux.
     The scanner and the budget tool are prepared by the quality gates job alone, on Linux
     arm64, so their preparation on Linux x64 and on Windows is new, as is the fixture supply on
     Windows. Whether the suite needs the commit trust is not established; a leg binds it so
     that its suite runs as the quality gates job's does.

## Risks / Trade-offs

- No leg has run. The first qualification after this Change lands is the first run of each. It
  may fail for the leg's own setup: the probe syncs its environment offline from the cache that
  the job's own sync filled, and that has run at Python 3.14 only. It may also fail for a test
  that has only ever run at Python 3.14, and a failed Linux leg fails the qualification that the
  release guide requires before the tag.
- The Windows leg may stop in its supply steps, before any test. It then gives no time.
- The `suite` class's timeout is not set from a measured duration, which the requirement
  `Hosted jobs bound their time and credentials` asks of a class. It stays provisional until legs
  have run.
- A qualification waits for the required legs, and `hosted checks` reports after them.
- The Linux legs block through `hosted checks`, which the release guide requires in prose. No
  operation of the product reads that check before a tag in this Change.
- A leg still blocks on a product file that no test executes on its platform. On Windows that
  judgment may fail the leg where the tests pass.
