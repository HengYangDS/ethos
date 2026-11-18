# Tasks

## 1. The admission

- [ ] 1.1 Add the six cases of an earlier sample: calm and old enough; absent; busy; not
      measurable; younger than one interval; calm but followed by a busy sample at admission.
      Done when all six fail without 1.2.
- [ ] 1.2 Let the admission take an earlier sample, and read the load in the proof operation
      before the readiness gates. Done when the six cases pass, the admission's existing tests
      pass unchanged, and the proof command's test shows the load read once before readiness.

## 2. Acceptance

- [ ] 2.1 Run one full proof of the lane on the host and read its gates' timeline. Done when no
      idle interval lies between the last readiness gate and the first test gate, or the
      proof's result names the wait and its reason.
- [ ] 2.2 Pass the precheck and readiness at the lane head. Done when each passes on the
      committed head and the hosted runs of that head pass on both forges.
