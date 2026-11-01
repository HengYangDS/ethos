# Proposal

## Why

ETHOS ships one Python behavior probe to every governed repository
(`src/ethos/adapters/gates/python_quality.py`) but proves its own suite through a second runner:
`tools/ci/python_test_gate.py` with an ordering plugin and a bytecode helper, reached through
`nox -s tests` and `nox -s coverage_floor`. A defect in the probe that adopters run cannot fail
ETHOS's proof. Reading the two side by side finds three such defects. The probe ignores the pytest
and coverage carriers that the repository paradigm itself declares. It stops every pytest run at 600
seconds whatever the gate declares. In a repository with mise configuration it needs a mise-declared
uv, which ETHOS does not declare. Each would stop ETHOS's own suite: without its pytest carrier the
suite runs serially, about 12,228 test-seconds, against a 600-second bound (found by reading; the
first task runs it).

The second runner also keeps ETHOS-only mechanisms in tools code: an evidence lock, completion
markers, shard handling, a separate coverage-floor gate, an Allure count check, a longest-first
plugin and a shared-bytecode step. The quality specification fixes one of them as an obligation
("native item-level work stealing") although the runner replaced it on 2026-09-18. The owner
approved rebuilding verification from the root on 2026-11-01 (decision D21), starting with this
Change.

## What Changes

- **One runner.** ETHOS's `unit-architecture` gate becomes a provider row of the shipped probe,
  `ethos.adapters.gates.python_quality:behavior_report`, declared the way adopters declare it. The
  `coverage-floor` gate goes; the execution that measures coverage decides the floor.
- **The probe runs under the repository's native test configuration.** When a repository declares
  the paradigm carriers, pytest runs with `.config/checks/pytest/pytest.toml` and the repository
  root as its rootdir, and coverage with `.config/checks/coverage/coverage.toml` and its source. A
  gate's `timeout_seconds` bounds the run, otherwise 600 seconds as before. Each attempt writes its
  JUnit report, report log and Cobertura report into its own report root, names that root to the
  test process, copies it to the runner's native output root when the runner names one, and removes
  its scratch through the shared owned-removal owner. Bytecode that the test process writes lands
  under the attempt's scratch (`PYTHONPYCACHEPREFIX`), never beside the repository's sources. A
  repository without the carriers keeps today's verdicts.
- **ETHOS's runner values become native configuration.** Workers are `-n auto --maxprocesses=12`,
  today's `min(12, CPUs)`; a hosted job selects its count through pytest-xdist's own
  `PYTEST_XDIST_AUTO_NUM_WORKERS`. The distribution mode is chosen by a measured cold run;
  `strict = true` replaces the two strict flags; `--durations=20` stays; the 95 percent floor is
  coverage's own `fail_under`. The suite's process environment and its Allure results move into
  `tests/conftest.py`.
- **A report-only tier guard.** A PEP 578 audit hook records, for each case, the files, directories,
  processes, databases and sockets its call crossed and whether that exceeds the tier its directory
  states. It never changes an outcome; `test-tiers` arms it.
- **Hosted acceptance reads the same attempt.** Hosted verification names its evidence directory as
  the native output root, takes the test and coverage figures from the probe's evidence, refuses
  Allure results whose case identities differ from the execution's, which replaces the count check,
  and renders the Allure views.
- **Deleted:** `tools/ci/python_test_gate.py`, `python_test_order.py` and `python_test_bytecode.py`;
  the `tests` and `coverage_floor` Nox sessions and the duplicate pytest run in the
  `architecture_projection` session; `.config/checks/coverage/policy.toml`; the product check of the
  deleted runner's source text; `junit_report`; the environment inputs only the runner read.
- **BREAKING** for contributors and operators: `nox -s tests` and `nox -s coverage_floor` no longer
  exist; `ETHOS_TEST_*` and `ETHOS_COVERAGE_LOCK_WAIT_SECONDS` have no effect; inside a proof,
  failure history and recorded durations no longer order the tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: ETHOS proves its Python suite through the probe it ships; the probe applies the
  repository's native test configuration and keeps its reports to one attempt; ETHOS reports what
  each case crosses; the test execution decides the coverage floor; distribution is stated as an
  obligation; attempt completion markers retire.
- `repository-governance`: the shared coverage-evidence lock and the caller-managed test basetemp
  retire with the runner that needed them.

## Impact

- Product: `src/ethos/adapters/gates/python_quality.py` and `code_quality.py`;
  `src/ethos/repository/policy/artifact_entrypoints.py`, `references/carriers.py` and
  `quality_reports.py`. About minus 14 effective lines.
- Tools: three modules deleted; `tools/ci/sessions.py` and `hosted_verification.py` changed. About
  minus 570 effective lines.
- Tests: the runner's own cases are removed, moved or re-targeted, each with a disposition in
  design.md; a single-runner regression, probe cases, the guard and its cases are added. About minus
  470 effective lines.
- Configuration and CI: `system/repository-gates.toml`, `system/surfaces.toml`, the pytest and
  coverage carriers, `.config/ci/pipeline.cue` and its GitLab projection. Documents: README, the
  configuration reference, the generated-artifact topology, the terminal plan's coverage-policy link
  and CHANGELOG.
- Adopters: the probe changes alter a verdict only in a repository that declares the paradigm
  carriers or a gate timeout above 600 seconds for Python tests. Every other run is unchanged,
  except that its test process sees `ETHOS_NATIVE_OUTPUT_DIR`, as the test command of a gate with
  native outputs already does, and writes its bytecode under the attempt's scratch. On the owner's
  workstation (2026-11-01), of the four repositories that run the probe, only
  web-ingestion-benchmark has Python, and it declares neither; other hosts are not verified.
- Builds on `probe-supply`, which declared uv in ETHOS's mise configuration, provisioned mise Python
  and uv on both hosted planes and rebound the GitLab supply image.
- Out of scope: identity completeness against the intended set (`verification-spine`), the order
  session at the release, ty over tests (`ty-over-tests`), arming the guard (`test-tiers`), the
  encoding rule, the shared JUnit reader's flaky-element refusal (a contract-2 row), ETHOS's
  JavaScript tests through the shipped JavaScript probe, and the host-conformance and supply-image
  pytest smokes (`platform-matrix`).
