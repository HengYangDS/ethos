# Tasks

## 1. One owner per behavior

- [x] 1.1 Add the gate. Done when `tests/architecture/test_parallel_implementations.py` fails at the
      base with the 16 measured groups and refuses a planted renamed copy. Evidence:
      `tests/architecture/test_parallel_implementations.py` failed at 42b08a1ca with the 16 measured
      groups while its planted case passed (15:37:2x). Review fixes in 3cb4d2058 extend the bound
      names to `except ... as`, nested definitions, imports and `match` captures, which the earlier
      gate missed (it grouped none of a planted `except ... as` pair), and add a test that the
      workflows' standalone scripts import only the standard library, which failed on 933c18107.
- [x] 1.2 Sink every copy into its owner. Done when the gate passes and Ruff, ty and the impacted
      tests pass. Evidence: at 03d9a7d45 the gate finds 0 groups; Ruff and ty pass. The impacted
      sweep of 423 targets ran 6,081 tests without a failure before its 3,000-second bound (15:39:35
      to 16:29:42); the 2,149 tests it did not reach and the fix-affected files then ran with 14
      failures (16:33:05 to 16:42:01), all six call sites of the removed request digest method in
      three retirement test modules that the type gate does not check, and those modules passed
      after 03d9a7d45 (127 passed, 16:45:30 to 16:49:34).

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: the precheck passed against 42b08a1ca with 0 findings (16:53:51 to 16:53:55),
      and readiness passed 28 gates at 03d9a7d45 with the 6 heavy gates left to the proof (16:50:49
      to 16:53:25).
