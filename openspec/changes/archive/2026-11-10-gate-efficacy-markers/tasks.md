# Tasks

## 1. Mechanism

- [x] 1.1 Register the `gate(id, role)` marker and the `gate_marks` plugin. Done when an
      unregistered id or role fails at setup, a skipped or xfailed marked test fails, and each mark
      appears in `user_properties`, all shown by an inner two-worker pytest run.
      `test_a_marked_test_cannot_skip_and_names_a_registered_gate` ran an inner two-worker pytest
      from 11:34:02 to 11:34:23: the skipped and the xfailed marked tests failed, the unknown gate
      errored at setup, the proving test passed, and its mark was the report property `ethos.gate`
      `commit-ranges:refusing`.
- [x] 1.2 Add the credited ledger and its whole-suite coverage check. Done when the check passes
      with the first slice's marks, and fails when a credited mark is removed. `CREDITED` in
      `tests/architecture/test_gate_efficacy.py` holds the first slice's six pairs. Its coverage
      check compares the marked pairs of a whole-suite run with the ledger, so removing a credited
      mark fails it; subset runs skip it with that reason.

## 2. First slice

- [x] 2.1 Mark `commit-ranges` and `format-selection` in their three roles and credit them. Done
      when each refusing test fails against a recorded mutant of its gate's policy and passes
      without it. `commit-ranges`: its refusing test failed at 11:35:36 against a mutant that
      dropped the per-range policy gaps and passed again at 11:35:55. `format-selection`: its
      refusing test failed at 11:36:08 against a mutant that disabled the empty policy-root check
      and passed again at 11:36:12. Both gates are marked in their conforming and fail-closed tests
      too.

## 3. Acceptance

- [x] 3.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there. The precheck passed with 0 findings on the Change's tree. Its impacted
      sweep of 35 test files passed 283 tests from 11:38:06 to 11:39:01, and the whole-suite
      coverage check skipped as a subset run. Readiness passed 28 gates from 11:40:13 to 11:42:20 at
      `2415458f3`.
