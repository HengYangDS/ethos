# Tasks

## 1. Resilient observation

- [x] 1.1 Specify the behavior with failing tests. Done when tests fail for these cases: a Python
      audit with no report and a failed request, retried with the backoff; acceptance reporting
      `advisory_request_failed` without parsing; and the gate's declared budget. Seven tests failed
      first.
- [x] 1.2 Classify Python request failures, retry both ecosystems with the backoff, and end
      evaluation early for unobserved checks. Done when those tests and the existing audit tests
      pass. All 136 dependency audit tests pass; Ruff and Ty report nothing.
