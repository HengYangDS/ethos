# Tasks

## 1. The reclamation reader

- [x] 1.1 Add the regressions before the change: four cases of
      `test_a_listed_path_that_cannot_be_looked_at_is_an_observed_absence` in
      `tests/unit/adapters/repo/runtime/test_retirement_listing.py`, with one marker for a closed
      directory in the suite's support module. Done when, without the change and under Python
      3.12 and under 3.13, the cases `below`, `alias` and `generation` fail with a deferred result
      that holds the permission error, and the case `link` passes.
      (With the test files of `4ec90091a` and the reader of `58fee6ae0`: under Python 3.12 and under
      3.13 the cases `below`, `alias` and `generation` fail and `link` passes; under 3.14 the four
      pass. The marker is in the suite's support module.)
- [x] 1.2 Ask the name itself in `_native_path`, and the directory question only of a name that
      is there. Done when the four cases of 1.1 pass under Python 3.12, 3.13 and 3.14, the
      existing cases of the module pass there too, and the source budget shows no growth of the
      product.
      (At `4ec90091a` the listing module, the host retention module and the writers module pass
      under Python 3.12, 3.13 and 3.14, 52 cases each; the listing module and the four modules that
      import the reader pass in the lane, 109 cases and 1 skipped. The product reads 83,206
      line-equivalents before and after.)
- [x] 1.3 Make the regression of a path deleted while it is observed delete the path inside the
      question that the reader asks, and assert that the deletion happened. Done when the case
      fails with the reader's handling of a deleted path removed and passes with it.
      (Before the reader's change the case `deleted` fails on the three interpreters, because the
      earlier reader asks another question. At `4ec90091a`, with the handling of a deleted path
      removed in a disposable clone, the case fails; with it, it passes.)
- [x] 1.4 Record the fix under `[Unreleased]` in `CHANGELOG.md`. Done when Prettier and the prose
      gate pass.
      (The line is under Fixed in the unreleased entry in `4ec90091a`; the commit helper's Prettier
      and prose checks pass.)

## 2. The link that names itself

- [ ] 2.1 Write the case first: a selector that names a local runtime whose path is a link to
      itself. Done when the case fails under Python 3.12 with an error that leaves the host
      store's cleanup, and its result under 3.13 and 3.14 is recorded.
- [ ] 2.2 Read such a selector as an unknown consumer on every interpreter. Done when the case
      of 2.1 passes under Python 3.12, 3.13 and 3.14.

## 3. The lane and the hosted runs

- [ ] 3.1 Review the code head, pass the precheck and readiness, and read the hosted runs of the
      head on both forges. Done when each passes on the committed head.
