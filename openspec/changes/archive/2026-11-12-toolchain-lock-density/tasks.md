# Tasks

## 1. Decision density

- [x] 1.1 Extract the lock checks and drop the stale pin. Done when the decision-density test fails
      before the change and passes after it, and the toolchain and mise tests pass. Evidence:
      e3b70d646 moves the two lock checks into `_lock_gaps` and drops the stale pin. The
      decision-density test failed before it with `toolchain_gaps` at 16 and the stale pin (21:23:38
      to 21:23:41), and passed after it with the toolchain and mise tests (62 passed, 21:24:00 to
      21:24:06); the architecture suite passed (300 passed, 21:24:46 to 21:25:17), and the
      precheck's 329 impacted test targets passed (6,322 passed, 21:25:33 to 21:58:01).

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: the precheck passed against dcc8e13a0 with 0 findings (22:00:19 to 22:00:22),
      and readiness passed 28 gates at dcc8e13a0 with the 6 heavy gates left to the proof (21:58:54
      to 22:00:07).
