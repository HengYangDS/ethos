## Why

The product Python behavior verifier rejects an unmodified pytest report whenever a test uses subtests. Since pytest 9, the JUnit suite total counts passing subtests, but JUnit emits no test case for them. A unittest `subTest` loop of 20 cases therefore reports `tests="97"` with 77 test cases. The provider path compares those two numbers and blocks with `quality_behavior_junit_suite_count_mismatch`, so an adopter that uses subtests can never prove its behavior axis.

The native observer path already handles this: it reads pytest's report-log events, which explain the totals that JUnit omits. The provider path never captures those events.

The provider behavior verifier also blocks when tests execute committed tooling. Coverage measures every repository file that a test executes, but the provider bound the coverage report only to product source and test files. A test that runs a tooling script therefore blocked with `quality_behavior_coverage_file_unbound`, although tooling owes no behavior coverage.

The product Python static provider also disagrees with the governed repositories on line width. It runs Ruff isolated from repository configuration, as it must, but leaves the width at Ruff's 88-column default. Every explicit formatter width in the governed repositories is 100, ETHOS's own Ruff configuration included. A provider adopter formatted at that width fails `E501` on every line from 89 to 100 columns.

## What Changes

- The provider behavior run also writes pytest's report-log.
- It validates the JUnit report against those events with the same reader as the native path.
- A run that writes no event report blocks as `test_event_report_missing` unless the command itself failed.
- Provider coverage binds to every committed Python subject; only product source still has to be measured and exercised.
- The isolated provider Ruff run measures lines at the shared width of 100 columns.

## Impact

- Code: `src/ethos/adapters/gates/python_quality.py`.
- Tests: the real locked provider test gains a subtest case and a case whose test executes tooling, and the static provider gains a width case.
- Specs: quality gains three requirements for provider evidence.
- Consumers: a Python adopter on the provider path needs `pytest-reportlog` in its locked dev environment, beside `pytest` and `pytest-cov`. The product quality-sample fixture already locks it. Adopters on the native observer path are unaffected. The wider line limit only admits lines that 88 columns rejected.
