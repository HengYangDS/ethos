# Tasks

## 1. A foundation starter that passes its paradigm

- [x] 1.1 Author the two carriers, apply the paradigm's repairs and check the composed candidate in
      formation. Done when the formation test that requires an empty paradigm report fails before
      the change and passes after it, a composition with a gap refuses before any target exists, and
      the greenfield, Python starter and starter evolution tests pass. Evidence: 66fbac7c8 adds
      `starter/conformance.py` and calls it from formation. Before the change the formed commit had
      8 paradigm gaps (measured 18:37:46 to 18:37:55 at 487075229) and the new tests could not
      import the conformance module (20:20:47 to 20:20:51); after it, the empty-report,
      planned-files and refusal tests passed (20:22:19 to 20:22:26), all 19 greenfield tests passed
      (20:34:07 to 20:34:31), and the 29 formation, starter and evolution targets passed except the
      public CLI preview test, which pinned the old planned files and now reads the direct plan (611
      passed, 20:28:13 to 20:33:36).
- [x] 1.2 Add the Fixed line to `CHANGELOG.md`. Done when Prettier and Vale accept it. Evidence:
      66fbac7c8 adds the Fixed line; Prettier and Vale accepted it in the commit's checks.

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: the precheck passed against c9d5ebf22 with 0 findings (20:43:23 to 20:43:32),
      and readiness passed 28 gates at c9d5ebf22 with the 6 heavy gates left to the proof (20:44:02
      to 20:46:11).
