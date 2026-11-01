# Design

## Context

See [proposal.md](proposal.md). Verification design 3.4 makes the probe ETHOS ships the one test
runner (V1) and lists its rules. This Change implements the rules that wait for neither the intent
spine nor the tier directories nor the contract integer.

At `63deedc09` the probe runs
`uv run --locked --offline [--python <mise Python>] python -m pytest -q -W error -o cache_dir=<scratch> --basetemp=<scratch> --junitxml --report-log --cov=. --cov-branch --cov-report=xml <top-level test directories>`
in a temporary directory, bounded at 600 seconds. It judges JUnit against the report log, the
coverage of every product file and the exit status (`python_quality.py:210-327`). ETHOS's gate
instead runs Nox, which assembles an environment, compiles shared bytecode, orders tests by recorded
duration, runs pytest with its explicit configuration, renders Allure, copies native outputs and
leaves coverage data for a second gate (`tools/ci/python_test_gate.py`;
`tools/ci/sessions.py:166-192`).

Task 2.3 records here what ETHOS's suite does through the probe once it applies the repository's
carriers. Its first run, at `5734e7dbe` with 12 workers, stopped after 205 cases in 46 seconds on
the carrier's `--maxfail=1`, on removals this Change had not yet made: two
`test_python_test_gate.py` floor cases read the deleted `policy.toml`, and the product-boundary
closure reported the remaining `policy.toml` references and an `allure_pytest` import in hosted
verification that the deptry module map (`allure-pytest=allure`) does not own. So task 2.3 observes
again after task 5.4. One case skipped because no native checksum tool is on the probe's locked PATH
(`tests/architecture/ci/test_supply_contract.py:162`). The run also wrote Hypothesis's constants
cache, 5,340 files, into the lane's `build/runtime/tool-cache/hypothesis/gw0` to `gw11`: Hypothesis
6.170.14 caches the constants of local source even without an example database
(`hypothesis/internal/constants_ast.py:219-252`), which Decision 14 answers.

## Goals / Non-Goals

**Goals:**

- ETHOS's proof runs its Python suite only through the shipped probe, so a probe defect fails it.
- The probe honors the configuration the paradigm tells every repository to declare.
- No runner holds ETHOS-specific values: they live in ETHOS's native configuration and its own test
  support.
- Every case's crossings are visible before `test-tiers` moves cases by them.

**Non-Goals:**

- The items of VD 5 row 2 that other owners carry, each on its route: identity completeness against
  the intended set and arming the guard (`test-tiers`); the order session (`release-prepare`, its
  first verification step, with argument variation from `probe-rows`); ty over tests
  (`ty-over-tests`, the route row after this Change); the JUnit flaky-element refusal for every
  repository (a contract-2 row), while ETHOS's own run refuses a `rerun` outcome through the
  report-log agreement (task 5.5); the encoding rule (`unit-rewrite`, which first makes the 1,321
  implicit encodings explicit); and Allure labels, history and publication (`allure-full`).
- V1 for ETHOS's JavaScript Nox session (`javascript-probe`), the host-conformance node IDs and the
  supply-image smoke (`platform-matrix`). This Change meets V1 for Python tests on the proof plane.
- Changing any adopter's verdict through an ETHOS rule. The probe applies only carriers a repository
  declares itself. On the owner's workstation the repositories with a `behavior_report` row are
  aigw-cli, architecture-publications, architecture-publisher, web-ingestion-benchmark and
  openai-responses-proxy; only the proxy declares the carriers, and its row judges its own Nox
  outputs (`execution_mode = "subprocess"`, `.ethos/profile.toml:80`), which never reach the probe's
  run (`python_quality.py:368-369`). No Python-running row declares `timeout_seconds`, and none of
  them uses Hypothesis.
- Recovering test time lost with longest-first ordering: the throughput Changes own the 900-second
  threshold (QS 1778-1791; verification design 3.8).

## Decisions

1. **The shipped probe is ETHOS's test gate.** `unit-architecture` becomes a provider row of
   `ethos.adapters.gates.python_quality:behavior_report` with `execution_mode = "provider"` and
   `tool_adapter = "ethos"`, which the quality obligations require to read its evidence
   (`quality/obligations.py:190-203`). It keeps `profile = "product-toolchain"`, so the provider
   source is bound to the lane's own `src/ethos` (`quality/sources.py:140-155`) and a proof run from
   another package is refused (`verification.py:245-274`, QS 2654). It keeps its dependencies,
   `cpu_reservation`, `writes_files` and its `repository`, `supply` and `evidence/tests` locks; the
   `scratch/tests` lock leaves with the runner's shared basetemp. The gate id stays, because the
   starter rule and the specifications name it (`src/ethos/repository/policy/rules/compile.py:59`).
   Alternatives rejected: a command row running pytest directly, which is a second runner; the
   code-quality provider, which would also run ETHOS's JavaScript tests a second time beside
   `javascript-tests`.
2. **Carriers by location, with the root as rootdir.** The probe uses a carrier only when the file
   exists at the paradigm location (`NATIVE_TOOL_LOCATIONS`, `tool_configuration.py:9`). With `-c`
   it passes `--rootdir=<root>`, because pytest otherwise takes the configuration file's directory
   as rootdir and node identities would begin with `../../..`, which the report-log reader refuses
   (`quality/pytest.py:109-123`). It does not call `native_repository_configuration`
   (`native/inputs.py:211-223`), which raises for a root `pytest.toml` or `.coveragerc` that pytest
   and coverage still read natively today, as the probe's own strict-config case does
   (`tests/unit/adoption/quality/test_python_quality.py:74-77`). With a coverage carrier it passes a
   bare `--cov`, so the carrier's `source` applies; `--cov=.` (`python_quality.py:253`) would
   override it. Rejected: ETHOS-specific flags inside the probe (an owned literal and a second
   owner); allowing `PYTEST_ADDOPTS`, which the probe removes so that ambient configuration cannot
   change a verdict (`python_quality.py:258-264`, QS 98-109); a root `pytest.toml` in ETHOS, which
   the paradigm refuses as a competing carrier (`tool_configuration.py:37-49`).
3. **The floor is coverage's own `fail_under`.** pytest-cov 7.1.0 takes `fail_under` from the
   coverage configuration when no `--cov-fail-under` is given and fails the session when coverage is
   lower (`pytest_cov/plugin.py:270-271, 369-380` in the locked environment), so the execution that
   measured coverage decides the floor, and the report log's exit status carries it.
   `.config/checks/coverage/policy.toml` loses its only reader (`python_test_gate.py:339`) and goes;
   QS 114-115 and the terminal plan's coverage-policy link (TP 119-121) name the coverage carrier
   instead. Rejected: a `coverage-floor` provider reading the probe's percentage (new product code);
   the probe reading `policy.toml` (an ETHOS path inside the product).
4. **The gate bounds the run.** The probe passes the gate's `timeout_seconds` to `run_command`,
   otherwise 600 seconds; `code_quality.py` passes it through for Python as well. ETHOS declares
   `timeout_seconds = 7200`: a stall bound, about eight times the workstation gate time (895.1 s)
   and above an estimated four-worker hosted run (12,228 serial test-seconds measured on 10-31,
   divided by 4, about 3,060 s; unmeasured). The per-test hang limit stays 600 seconds (QS
   2866-2883). Rejected: raising the probe's default, which would change every adopter.
5. **Reports belong to the attempt; the runner decides where copies go.** The attempt's report root
   holds `pytest/junit.xml`, `pytest/events.jsonl` and `coverage/coverage.xml`, the layout hosted CI
   already uploads (`.config/ci/pipeline.cue:311-313, 564-575`). The probe names the root to the
   test process as `ETHOS_NATIVE_OUTPUT_DIR`, the existing name of the runner's native output root
   (`system/surfaces.toml:25`; `native/attempt.py:152`), so a suite may add native results there,
   and copies the root to the outer `ETHOS_NATIVE_OUTPUT_DIR` when the runner names one. Scratch is
   removed through `remove_owned_path` (`runtime/filesystem.py:65`), which keeps QS 2233-2253 true
   for test output now that the probe owns it. The probe also points `PYTHONPYCACHEPREFIX` at the
   attempt's scratch, so bytecode that the test process, or a child that keeps the environment,
   writes lands there and leaves with it instead of beside the repository's sources (committee round
   10). Refusing a test's other writes to ignored paths waits for the kernel's scratch roots
   (`probe-rows`), because it would change adopters' verdicts. Rejected: retaining each attempt in
   `.git/ethos/artifacts` with `retain_attempt` (`javascript/execution.py:32-50`), a new per-proof
   artifact in every adopter with no consumer and no exit (P6); writing into `build/evidence` from
   the probe, which adopters have not admitted.
6. **ETHOS's environment and Allure are ETHOS's test support.** `tests/conftest.py` sets, at import
   and so before workers start, what the runner set for the whole pytest process (TG:383-402): Git
   configuration hidden, with `core.fsmonitor=false` replacing any inherited `GIT_CONFIG_*` overlay
   (the per-test fixture merges inherited entries, `tests/conftest.py:72-89`); no terminal prompt;
   no bytecode writes (`PYTHONDONTWRITEBYTECODE` for children, `sys.dont_write_bytecode` from the
   conftest on); an absolute `UV_CACHE_DIR`; one `ETHOS_NODE_PACKAGE_SUPPLY`, resolved once; no
   inherited `ETHOS_ACTOR`. A `tryfirst` `pytest_configure` points allure-pytest at
   `<report root>/allure/results` when `ETHOS_NATIVE_OUTPUT_DIR` is set, because allure-pytest reads
   its directory option at configure time (`allure_pytest/plugin.py:152-170`); the per-test fixture
   then removes the variable so nested commands cannot write into the attempt's root. The shared
   bytecode step retires: test processes still write no bytecode, so each child compiles what it
   imports, in a scratch environment that uv does not compile. Task 7.2 measures the cost; if it is
   material, `UV_COMPILE_BYTECODE=1` in the probe (one line, every adopter, installed packages only)
   or the checked-hash compile step moved into `tests/support` restores it. Rejected: the probe
   passing `--alluredir`, which needs plugin detection and is visible to adopters.
7. **The guard reports from ETHOS's test support.** `tests/support/tier_guard.py`, loaded from
   `tests/conftest.py`, installs one audit hook per process (PEP 578). The hook acts while a case's
   setup, call and teardown run, so work moved into a fixture is still the case's (committee round
   11). It records `open`, `os.listdir`, `os.scandir`, `os.remove`, `os.rename`, `subprocess.Popen`,
   `os.system`, `os.posix_spawn`, `os.fork`, `sqlite3.connect` and `socket.connect`.
   `sqlite3.connect` is added to VD 3.4's list because SQLite opens its file without an `open` event
   and the Lease store is SQLite. An event is not the case's when the first frame outside the
   standard library loads a module (`_frozen_importlib*`, `importlib`, `zipimport`; F11) or belongs
   to a test tool (pytest, pluggy, Hypothesis, coverage, Allure, xdist, pytest-timeout), when its
   path is under the attempt's report root, or while a fixture wider than function scope is set up,
   which would otherwise charge whichever case requests it first. A case under `tests/unit/` exceeds
   its tier on any recorded event; any other case exceeds it only on a connection beyond loopback; a
   Unix-domain socket counts as local, and DNS lookups (`socket.getaddrinfo`) are not recorded. The
   hook appends `ethos.crossed` and `ethos.exceeds` to `item.user_properties`, which pytest writes
   into the case's JUnit properties (`_pytest/junitxml.py:546-547`) and the report log. Rejected: a
   product plugin now (7 lines of product headroom at `63deedc09`; an adopter rule needs contract
   2); a separate JSON report (another evidence file; V8).
8. **Distribution.** `-n auto --maxprocesses=12` reproduces today's default (`os.cpu_count()` is 18
   on the reference workstation, and psutil is not locked, so `auto` is 18 and the cap gives 12);
   hosted jobs set `PYTEST_XDIST_AUTO_NUM_WORKERS` instead of `ETHOS_TEST_WORKERS`
   (`xdist/plugin.py:15-28, 310-324`). A focused run inherits the workers; `-n 0` gives a serial
   run. The mode starts as today's `--dist=load --maxschedchunk=1`; task 7.1 keeps it or switches to
   `worksteal`, whichever cold run is faster (VD 3.4). The probe's pytest cache is per attempt
   (`python_quality.py:248-249`), so longest-first ordering and `--failed-first` have no history
   inside a proof; `fast-tier` owns selection from recorded facts (V6). Rejected: moving the
   ordering plugin into `tests/support`, where it would be inert; keeping a cache under the Git
   common directory for every repository, a new adopter store root where DD move 5 retires
   `tool-cache`.
9. **Report agreement replaces the count check.** ETHOS's run now carries the report-log agreement
   (`quality_reports.py:127-138`): case identities and outcomes must match JUnit, and a `rerun`
   outcome is invalid (`quality/pytest.py:29`). Hosted acceptance compares the multiset of Allure
   `fullName`s with one `<classname>#<name without parameters>` per executed instance in the report
   log, the form allure-pytest 2.16.2 builds (`allure_pytest/utils.py:140-145`). That is stronger
   than the count it replaces (TG:293-301; VD section 4), and JUnit's extra error case for a failing
   teardown cannot skew it. `--max-worker-restart=0` stays the no-replay rule, and its regression is
   re-targeted.
10. **`strict = true`.** pytest 9.2 enables `strict_config`, `strict_markers`, `strict_xfail` and
    `strict_parametrization_ids` with it (`_pytest/main.py:94-117`). The suite has no `xfail`. Two
    parametrizations relied on pytest's numbered `<lambda>` ids
    (`test_mutable_or_interpreted_reads_are_observed_every_time` and
    `test_relocated_tasks_still_refuse_body_and_task_changes`); they get explicit ids, so their 12
    node identities change and task 5.6 maps them. Stable ids are what identity completeness and
    selection by recorded facts key on.
11. **Deletion follows disposition (V2).** Each removed case is superseded by a named case or
    rejected with its reason, in the table below.
12. **Hosted verification consumes the probe's evidence.** Test and coverage figures come from the
    probe's provider report in the executed proof, selected by its provider reference, not from
    re-parsed files, and a run in which every case skipped is refused; the files are kept for upload
    and for the GitLab reports. The Allure render moves from the runner into hosted verification
    with the same Allure 3 command (TG:258-287).
13. **Completeness is accepted once against the parent runner.** Until `test-tiers` arms the spine
    gate, the probe must execute exactly the node identities that the parent tree's runner executed
    in the base proof, minus the removed cases below and plus the cases this Change adds
    (verification design 5, committee round 10). Any other difference blocks the landing; an
    identity the probe no longer collects is never accepted silently.
14. **Hypothesis is reproducible and its storage stays in the attempt.** `tests/conftest.py`
    registers and loads a `proof` profile, derandomized with no deadline and no example database (VD
    3.5), unless `--hypothesis-profile` selects another; Hypothesis's own `ci` profile no longer
    differs from a local run. The probe points Hypothesis's native `HYPOTHESIS_STORAGE_DIRECTORY` at
    the attempt's scratch, as it does `COVERAGE_FILE` and `PYTHONPYCACHEPREFIX`, and the conftest
    chooses `build/runtime/tool-cache/hypothesis/<worker>` only when that variable is absent, so a
    direct run keeps its cache and a probe run leaves nothing (Context). The guard's path exemption
    for that cache goes: Hypothesis's work is a test tool's (Decision 7). The `deep` profile and its
    per-worker database belong to the release (VD 3.5). Rejected: `TMPDIR` into scratch, which
    lengthens every temporary path past macOS's 104-byte socket limit and Windows's path limit; a
    database-free profile alone, which still writes the constants cache.

### Case dispositions

| Removed case                                                                                                     | Disposition                                                                                                                |
| ---------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `test_python_test_gate.py::test_parallel_python_test_gate_bounds_failed_attempt_without_replay[4]`               | kept, moved to `test_pytest_configuration.py`; runs ETHOS's configuration directly (QS 224-233, 1907-1938)                 |
| `::test_coverage_gate_is_in_the_resolved_proof_closure[2]`                                                       | superseded by `test_single_test_runner.py` (the test gate is in both proof sets)                                           |
| `::test_coverage_floor_rejects_below_required_measurement[94, 95]`                                               | superseded by the floor boundary case (QS 235-243)                                                                         |
| `::test_native_outputs_reach_the_selected_root[2]`                                                               | superseded by the probe's report-root case                                                                                 |
| `::test_coverage_database_is_ready_before_selected_test_execution[2]`                                            | rejected: it guarded the shared evidence home, which retires; a failing coverage database fails the run natively           |
| `::test_failed_python_attempt_observes_capacity_before_temp_cleanup`                                             | rejected: diagnostic output of the retired runner; the probe keeps pytest's native stderr                                  |
| `::test_native_tmp_path_policy_reclaims_passed_case_before_next_case`                                            | kept, moved (`pytest.toml:5`)                                                                                              |
| `::test_native_failure_report_never_renders_frame_arguments`                                                     | kept, moved (the bounded failure report, `pytest.toml:3`)                                                                  |
| `::test_python_cleanup_changes_only_required_directory_permissions[4]`                                           | kept, moved to `test_filesystem.py` (QS 2233-2253)                                                                         |
| `::test_python_cleanup_preserves_external_content_and_permissions[3]`                                            | kept, moved to `test_filesystem.py` (QS 2233-2253)                                                                         |
| `::test_python_attempt_revokes_previous_success_before_any_work[4]`                                              | rejected with the removed requirement "Test attempt completion is committed last"                                          |
| `::test_python_single_attempt_discards_partial_and_sharded_outputs`                                              | rejected, same requirement                                                                                                 |
| `::test_killed_python_attempt_cannot_reuse_previous_completion`                                                  | rejected, same requirement                                                                                                 |
| `::test_python_basetemp_ownership[...]`                                                                          | rejected with the removed RG requirement "Python test basetemp has one explicit owner"                                     |
| `test_python_test_bytecode.py::test_test_processes_reuse_gate_bytecode_without_stale_or_new_writes`              | rejected: shared bytecode retires; the conftest keeps "write none" (`PYTHONDONTWRITEBYTECODE`); cost measured              |
| `test_python_test_order.py` (3 cases)                                                                            | rejected: a per-attempt cache has no recorded durations; the mode is measured (task 7.1)                                   |
| `test_allure_reporting.py::test_test_gate_replaces_stale_allure_results_in_the_same_attempt`                     | superseded by hosted verification clearing its evidence directory (QS 2385-2389)                                           |
| `::test_report_reconstruction_refuses_missing_and_stale_source`                                                  | superseded by hosted verification refusing missing results                                                                 |
| `::test_report_rebuilds_from_one_failed_pytest_attempt_without_rerun`                                            | kept, re-targeted to hosted verification's render (QS 2379-2383)                                                           |
| `::test_failing_test_session_still_renders_without_replacing_test_failure`                                       | superseded by a hosted render-after-failure case                                                                           |
| `::test_binary_parameter_cases_remain_distinct_in_native_agent_report`                                           | kept, re-targeted (QS 2391-2395)                                                                                           |
| `test_nox_toolchain.py::test_full_test_session_refuses_selectors_before_loading_supply`                          | rejected: the session is gone                                                                                              |
| `test_release_assets.py::test_python_test_sessions_receive_the_frozen_node_package_supply`                       | superseded by the conftest environment case (QS 210-220)                                                                   |
| `::test_test_environment_freezes_locked_supply_as_absolute_paths[...]`                                           | superseded by the conftest environment case and task 3.3's worker check                                                    |
| `test_artifacts.py::test_entrypoint_audit_reads_the_nox_python_test_owner`                                       | rejected: the check it covered is deleted                                                                                  |
| `test_parallel_proof.py::test_public_proof_stops_heavy_work_after_readiness_failure[*-package-coverage-floor-*]` | renamed to `[*-package-build-*]`: the dependency after the test gate becomes `build`, as the `coverage-floor` gate retires |
| `test_quality_reports.py::test_junit_requires_a_report`                                                          | rejected: the path reader is deleted; the stream reader refuses empty input as `junit_invalid`                             |

## Risks / Trade-offs

- [ETHOS's suite may not pass under the probe's environment: a scratch environment instead of the
  root `.venv`; mise's locked PATH without Homebrew Git, `/usr/sbin/lsof` or the tool paths that
  hosted verification prepends; `MISE_OFFLINE` and `MISE_CEILING_PATHS` set for every test; the
  report-log agreement at 7,780 cases under xdist, which no test or adopter has exercised; recorded
  warnings failing the run (`quality/pytest.py:223-229`)] → Task 2.3 runs it once, after the probe
  applies the carriers and before the suite's own configuration moves, and lists every refusal;
  fixes go into the suite's conftest, its test support or the probe within this Change, and the
  Change splits again if a product fix does not fit the margin.
- [A missed floor reports `quality_behavior_tests_failed`, with pytest-cov's "Coverage failure" line
  in the retained output, instead of its own gate] → Accepted: the gate id and output still name the
  cause; a distinct gap would be new product code.
- [The test gate may get slower: no longest-first order, no shared bytecode (its Change measured
  about 40 percent of one 37-process test spent compiling), a scratch environment per attempt, the
  guard] → Section 7 measures each against 895.1 s and records it; Decision 6 names the bytecode
  fallback; the throughput Changes own the 900-second threshold.
- [Fail-left inside proofs weakens: failure history no longer reorders] → Recorded as a measured
  trade-off; `fast-tier` restores fail-left by selection from facts.
- [Landing admission by the installed predecessor reads the new provider-row evidence] → The
  evidence keeps its `quality_evidence` keys (`python_quality.py:359-366`), and `entrypoint_files`
  skips the deleted runner (`references/carriers.py:139-153`); the landing preview runs with the
  installed predecessor before apply.
- [The guard's attribution has limits: a cached loader charges its first read to whichever case runs
  first, a wider fixture's finalizers run inside the last case's teardown, child processes are
  outside the hook, SQLite is seen only at connect] → It reports and never decides; `test-tiers`
  reads it with these limits.
- [QS 413-415 forbids "another wheel install" in Python tests, and the probe's scratch environment
  installs the project in editable mode] → The requirement constrains test content (no package
  acceptance replay), not the runner's environment preparation; if review reads it otherwise, this
  Change amends QS 445-446, which DD gives to `test-tiers`.
- [Local proofs no longer keep Allure results or render views] → Hosted verification keeps both; a
  local proof keeps the results when the operator names `ETHOS_NATIVE_OUTPUT_DIR`; `allure-full`
  gives both planes the redacted single-file report.

## Migration Plan

1. `probe-supply` lands and is published; the supply image is rebuilt from `dev` and its digest
   bound.
2. This Change: failing cases first, then the probe, ETHOS's native configuration, the guard, the
   registry switch, the deletions, hosted verification, specifications, documents and measurement;
   one full proof.
3. After landing, both hosted planes run the probe on the next published commit.

Rollback: revert the Change. The registry returns to the Nox gate; the probe changes are neutral for
adopters and may stay.

## Open Questions

- Should a probe keep a per-lane pytest cache with a declared owner, consumer and exit, as VD 3.5
  gives mutmut's cache? `fast-tier` decides with its selection design.
