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

- [ ] 2.1 Run one full proof of the lane on the host and read its gates' timeline. Done when no
      idle interval lies between the last readiness gate and the first test gate, or the
      proof's result names the wait and its reason.
- [ ] 2.2 Pass the precheck and readiness at the lane head. Done when each passes on the
      committed head and the hosted runs of that head pass on both forges.
