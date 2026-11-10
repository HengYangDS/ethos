# Tasks

## 1. One owner per behavior

- [ ] 1.1 Add the gate. Done when `tests/architecture/test_parallel_implementations.py` fails at
      the base with the 16 measured groups and refuses a planted renamed copy.
- [ ] 1.2 Sink every copy into its owner. Done when the gate passes and Ruff, ty and the impacted
      tests pass.

## 2. Acceptance

- [ ] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
