# Tasks

## 1. The admission

- [x] 1.1 Add the six cases of an earlier sample: calm and old enough; absent; busy; not
      measurable; younger than one interval; calm but followed by a busy sample at admission.
      Done when all six fail without 1.2.
      (On the landed code, in a scratch copy: the six cases fail (`6 failed`). They are
      `tests/unit/gates/test_proof_slot_earlier_sample.py` in `6344d93e3`.)
- [x] 1.2 Let the admission take an earlier sample, and read the load in the proof operation
      before the readiness gates. Done when the six cases pass, the admission's existing tests
      pass unchanged, and the proof command's test shows the load read once before readiness.
      (At `6344d93e3` the eleven test files that reach the two modules pass in the lane, 259 and 206
      cases, with `test_proof_slot.py` unchanged; the proof command's test asserts one read of the
      load before the readiness gates. `20bfa1258` moves the sample into two helpers, after which
      the architecture tests and the same proof modules pass, 158 cases.)

## 2. Acceptance

- [x] 2.1 Run one full proof of the lane on the host and read its gates' timeline. Done when no
      idle interval lies between the last readiness gate and the first test gate, or the
      proof's result names the wait and its reason.
      (Two full proofs of `7bd573ad9` on 2026-11-20 on the declared host, both proven. The last
      readiness gate ended 57.31 s and 46.94 s after the start, and the first test or package
      gate started 0.04 s and 0.03 s later. Each result names a wait of 0.0 s, at a load of
      6.80 and of 5.09 against the limit of 18.0.)
- [x] 2.2 Pass the precheck and readiness at the lane head. Done when each passes on the
      committed head and the hosted runs of that head pass on both forges.
      (At `7bd573ad9` on 2026-11-20 the pre-check passes with no finding and readiness passes with
      its 28 gates. The pre-check ran its full selection at `a9e90ab6f`, 413 test modules, 8,337
      passed and 3 skipped, and from there the selection of the one test file that differs, 43
      modules, 371 passed and 1 skipped.
      GitHub's push run 44655144202 and GitLab's pipeline 16815 of `7bd573ad9` pass. The run's
      link observation, which may fail, counted three redirects; `64c12fc64` names those
      sources at their new addresses.)
