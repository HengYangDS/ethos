## Why

The product Python behavior verifier rejects an unmodified pytest report whenever a test uses subtests. Since pytest 9, the JUnit suite total counts passing subtests, but JUnit emits no test case for them. A unittest `subTest` loop of 20 cases therefore reports `tests="97"` with 77 test cases. The provider path compares those two numbers and blocks with `quality_behavior_junit_suite_count_mismatch`, so an adopter that uses subtests can never prove its behavior axis.

The native observer path already handles this: it reads pytest's report-log events, which explain the totals that JUnit omits. The provider path never captures those events.

## What Changes

- The provider behavior run also writes pytest's report-log.
- It validates the JUnit report against those events with the same reader as the native path.
- A run that writes no event report blocks as `test_event_report_missing` unless the command itself failed.

## Impact

- Code: `src/ethos/adapters/gates/python_quality.py`.
- Tests: the real locked provider test gains a subtest case.
- Specs: quality gains one requirement for provider behavior evidence.
- Consumers: a Python adopter on the provider path needs `pytest-reportlog` in its locked dev environment, beside `pytest` and `pytest-cov`. The product quality-sample fixture already locks it. Adopters on the native observer path are unaffected.
