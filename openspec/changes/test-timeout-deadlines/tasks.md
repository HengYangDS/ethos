# Tasks

## 1. Deadlines

- [x] 1.1 Bound per-test timeouts by the tool deadline. Done when the three markers use
      `seconds("tool")`, the guard refuses a planted literal marker, and the affected tests pass.
      Evidence: at 0b7d543a5 the three markers use `seconds("tool")`, the guard
      `test_a_per_test_timeout_never_undercuts_the_tool_deadline` refuses a planted literal marker,
      and the four affected test modules passed (132 tests, run between 20:22:40 and 20:24:28).

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: ruff and its format check passed on the four modules at 0b7d543a5, and
      readiness passed 28 gates at 0b7d543a5 with the 6 heavy gates left to the proof (20:27:12).
