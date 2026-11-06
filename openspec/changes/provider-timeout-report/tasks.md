# Tasks

## 1. Late provider report

- [x] 1.1 Specify with a failing test that a provider returning after its deadline keeps its report
      in the gate's result, with an unknown verdict and `gate_timeout:<gate>`. Done when it fails on
      the current runner. Red at 01:32:38: the late report came back as `{"verdict": "unknown"}`.
- [x] 1.2 Keep the late report. Done when that test and the gate runner tests pass. Green at
      01:33:06: 36 runner tests pass; at 01:38:41 the gate, kernel and quality areas pass with 1,280
      tests.
