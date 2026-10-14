## Context

`python_quality._behavior_evidence` runs the adopter's locked pytest with JUnit and coverage output, then validates JUnit with `junit_report`. Without pytest events, that reader requires each suite's declared `tests` total to equal its emitted test cases. `junit_stream_report` takes the report-log events as well. It requires JUnit's emitted cases and outcomes to match the events, then takes totals from the events. The native observer path already uses it.

## Decisions

1. Reuse `junit_stream_report` instead of relaxing the suite-count check. Without events, an inflated total is indistinguishable from omitted subtests.
2. Pass `--report-log` without `-p pytest_reportlog.plugin`. The provider run keeps pytest plugin autoload, as it already does for `pytest-cov`, and loading the plugin a second time fails.
3. A missing event report blocks like a missing JUnit report: as the command failure when pytest failed, and otherwise as a missing report.
4. Pin the static width as a command argument, not through repository configuration. `--isolated` keeps the product rules from being weakened by an adopter, so the shared width of 100 has to be part of the product command itself.
