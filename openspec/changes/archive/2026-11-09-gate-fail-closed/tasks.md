# Tasks

## 1. Tests first

- [x] 1.1 Add the containment tests: graph serial and parallel, class preservation, provider errors,
      a report JSON cannot hold, the preview and the interrupt. Done when each behavioural test
      fails on the current code and the interrupt test passes there. The tests came first: from
      03:05:37 to 03:06:03 at `1f2738db3`, 55 failed and 153 passed. The 10 behavioural tests of
      `test_failure_containment.py`, three provider cases of
      `test_provider_exception_becomes_failed_result` and the 42 `raise` cases of
      `test_public_proof_stops_heavy_work_after_readiness_failure` failed, and
      `test_an_interrupt_still_stops_the_whole_run` passed. The process-evidence assertion failed in
      its 2 cases from 03:32:17 to 03:32:20.

## 2. Containment

- [x] 2.1 Add the containment rule and apply it at the provider seam and the gate seam. Done when
      the tests of 1.1 pass, with Ruff's `BLE001` ignored for exactly the two seam modules. At
      `421f46a85`, the containment tests and the moved observation's callers passed 389 tests from
      03:32:57 to 03:34:01, and Ruff's `BLE001` is ignored for exactly `verification.py` and
      `runner.py`.
- [x] 2.2 Move `observe_gate_execution` to `ethos.application.proof.host`. Done when no module
      imports it from the runner and `runner.py` is within the per-file ceiling. At `421f46a85`, no
      module imports `observe_gate_execution` from the runner; it lives in
      `ethos.application.proof.host`, and `runner.py` has 455 effective lines.

## 3. Acceptance

- [x] 3.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there. The precheck passed with 0 findings at 03:34:16 and readiness passed 29
      gates from 03:35:07 to 03:37:58, both at `421f46a85`. The impacted sweep of 114 test files ran
      from 03:15:00 to 03:30:46 at `1f2738db3` with the Change uncommitted: 2156 passed and 1
      failed, `test_readers_of_ethos_results_expand_them` on the report's JSON read-back. The
      committed serialization removed that read-back, and the 12 affected files then passed 389
      tests from 03:32:57 to 03:34:01.
