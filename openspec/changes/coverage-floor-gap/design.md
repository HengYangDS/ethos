# Design

## Context

`behavior_report` in `src/ethos/adapters/gates/python_quality.py` runs pytest with the repository's
coverage carrier, reads the JUnit, event and coverage reports of that one execution, and classifies
the run. A non-zero exit with no failed test, which is what pytest-cov's `fail_under` produces,
falls into `tests_failed`. The coverage measurement owner is
`src/ethos/repository/policy/quality_reports.py`.

## Goals / Non-Goals

Goals:

- A shortfall under the declared floor has its own gap and records the floor it was measured
  against.

Non-Goals:

- Moving the floor decision out of pytest-cov or keeping one floor decision per proof attempt; the
  `gate-reuse` Change owns that (R5).
- Other languages' coverage, which their providers decide.

## Decisions

1. **The measurement owner decides the floor.** `coverage_below_floor` in `quality_reports.py`
   takes the percentage, the floor and the precision and mirrors coverage.py: round to the declared
   precision, and a floor of 100 only by an exact 100, so the gap agrees with the exit that
   pytest-cov produced.
2. **Only an otherwise clean run is reclassified.** The pytest report owner now says whether a case
   failed, errored or warned, or none passed (`tests_failed`), apart from the session exit status
   that pytest-cov sets. Such a failure keeps `tests_failed`; a failed session whose cases are clean
   becomes `coverage_below_floor` when the measurement is under the floor, and stays
   `tests_failed` otherwise.
3. **The floor comes from the carrier the run used**, `.config/checks/coverage/coverage.toml`
   (`fail_under`, `precision`); without one, nothing is reclassified.

## Risks / Trade-offs

- The reclassification reads the carrier a second time. If the carrier changed between pytest's read
  and this one, the gap could disagree with the exit; the gate's execution-source check already
  refuses a source tree that changed during the run.
