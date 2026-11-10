# Tasks

## 1. Mechanism

- [ ] 1.1 Register the `gate(id, role)` marker and the `gate_marks` plugin. Done when an
      unregistered id or role fails at setup, a skipped or xfailed marked test fails, and each
      mark appears in `user_properties`, all shown by an inner two-worker pytest run.
- [ ] 1.2 Add the credited ledger and its whole-suite coverage check. Done when the check passes
      with the first slice's marks, and fails when a credited mark is removed.

## 2. First slice

- [ ] 2.1 Mark `commit-ranges` and `format-selection` in their three roles and credit them. Done
      when each refusing test fails against a recorded mutant of its gate's policy and passes
      without it.

## 3. Acceptance

- [ ] 3.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there.
