## 1. Reproduce The Authority/Execution Conflict

- [x] 1.1 Reproduce a staged official archive whose current-policy full proof is
  blocked on its original lane, while a detached proof cannot carry that
  lane's Lease. Assert the staged postimage and refs remain unchanged.

## 2. Separate Existing Owners

- [x] 2.1 Add an optional exact execution carrier to the existing proof path.
  Keep committed intent, policy, actor, Lease and issuance at the authoring
  root; run checks and source rechecks at a validated same-common-dir carrier.
- [x] 2.2 Reject wrong, attached, dirty, foreign or drifting carriers and any
  changed authoring HEAD, Lease, index or working content before proof issuance.
  Preserve completed-check diagnostics and unchanged ordinary proof behavior.
- [x] 2.3 Apply the previously authorized product source ceiling only in its
  native declaration after deletion review; retain the independent per-file,
  test, coverage and gate floors.

## 3. Qualify Candidate Inputs

- [x] 3.1 Run public positive and falsifying regressions, strict OpenSpec,
  formatting, lint, types, module-layout, and source-budget checks; freeze the
  exact candidate inputs for the subsequent full proof and lifecycle effects.
