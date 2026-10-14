# Tasks

## 1. Provider behavior evidence

- [x] 1.1 Capture pytest report-log events in the provider behavior run and validate JUnit against them; done when a locked fixture with passing subtests verifies and its total counts each subtest.
- [x] 1.2 Block a run that writes no event report; done when the missing report has its own reason and a failed command keeps `test_command_failed`.
- [x] 1.3 Measure isolated provider Ruff lines at the shared width of 100; done when a 100-column line passes and a 101-column line blocks with `E501`.

## 2. Verify

- [x] 2.1 Run strict OpenSpec validation, Ruff, ty and the Python quality evidence tests; done when all pass with no unrelated tracked change.
