# Tasks

## 1. Marks

- [x] 1.1 Time only the bounded operation. Done when the alias test's two-second mark is
      `func_only=True` over a fixture-built repository, the native-run marks are 60, the hang bound
      test refuses a planted tight mark without `func_only`, and the affected tests pass. Evidence:
      at 8c7479050 the alias test's two-second mark is `func_only=True` over the `alias_cycle`
      fixture, the native-run marks are 60, and `test_a_tight_timeout_times_only_its_test_function`
      refuses a planted tight mark; the affected modules passed (151 tests, 20:56:20 to 20:56:53)
      and the architecture tree passed from the lane root (281 tests, run through the kit between
      20:57:21 and 20:59:48).

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: ruff and its format check passed on the five modules at 8c7479050, and
      readiness passed 28 gates at 8c7479050 with the 6 heavy gates left to the proof (21:02:05).
