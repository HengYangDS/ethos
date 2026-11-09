# Tasks

## 1. Tests first

- [ ] 1.1 Add the containment tests: graph serial and parallel, class preservation, provider
      errors, a report JSON cannot hold, the preview and the interrupt. Done when each behavioural
      test fails on the current code and the interrupt test passes there.

## 2. Containment

- [ ] 2.1 Add the containment rule and apply it at the provider seam and the gate seam. Done when
      the tests of 1.1 pass, with Ruff's `BLE001` ignored for exactly the two seam modules.
- [ ] 2.2 Move `observe_gate_execution` to `ethos.application.proof.host`. Done when no module
      imports it from the runner and `runner.py` is within the per-file ceiling.

## 3. Acceptance

- [ ] 3.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there.
