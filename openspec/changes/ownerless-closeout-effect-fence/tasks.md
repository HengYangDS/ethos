## 1. Authority carrier

- [x] 1.1 Create a successor Work Lane from accepted dev without mutating the
  foreign predecessor lane.
- [x] 1.2 Record the approved effect-side safety design, scope, Claim, Chronicle,
  and executable implementation plan.
- [x] 1.3 Validate strict OpenSpec lifecycle and Claim digest bindings.

## 2. Red tests

- [x] 2.1 Add parameterized failures for every WCP response binding.
- [x] 2.2 Add late lease/Claim and same-target competing-decision failures.
- [x] 2.3 Add no-force, accepted-ref CAS, postcondition, receipt-binding, and
  partial-recovery inventory failures.

## 3. Implementation

- [x] 3.1 Add the strict WCP response adapter.
- [x] 3.2 Add the shared-state target fence and make lease acquisition respect it.
- [x] 3.3 Complete the clean ownerless CAS effect, non-zero-effect
  re-observation, three-state ref probe, and post-effect verifier.
- [x] 3.4 Complete typed receipt bindings, visible partial reservations, and
  receipt-present idempotent cleanup recovery.
- [x] 3.5 Split WCP, effect, cleanup, recovery, record, state, and inventory
  responsibilities into semantic modules while preserving only actual
  pre-existing caller entrypoints.
- [x] 3.6 Isolate the armed-hook E2E from the caller's writable editable runtime
  and assert that direct_url.json bindings do not drift.
- [x] 3.7 Close every Critical/Important whole-branch security-review finding
  with RED-to-GREEN regression evidence.
- [x] 3.8 Update command-plane documentation for clean ownerless WCP, fence,
  irreversible confirmation, partial states, receipt recovery, and cleanup.

## 4. Verification and lifecycle

- [x] 4.1 Fix WCP at main@5137759, verify source/host SHA equality, run 26
  ownerless plus 4 CLI tests, and record 59ee782 as superseded rather than
  cherry-picked.
- [x] 4.2 Run the final focused unit, schema, type, lint, security,
  command-contract, module-layout, and code-size gates.
- [x] 4.3 Run the full Python gate with the unchanged 100% coverage floor and
  close every report hard-floor gap.
- [x] 4.4 Complete independent task review and whole-branch
  security/simplicity review with no unresolved Critical or Important finding.
- [x] 4.5 Refresh generic parity in the admitted Work Lane and commit all
  tracked evidence.
- [x] 4.6 Run disposable cross-repository effect acceptance, workstation
  full/quick evaluation, task/lease/snapshot checks, and final housekeeping.
- [ ] 4.7 After every tracked pre-archive input is committed, execute the final
  exact-HEAD pre-archive implementation proof and confirm isolated official
  OpenSpec archive preflight is ready.

## Post-archive transition boundary

After every checkbox is complete, independently run the official archive,
migrate the Claim carrier, fuse the canonical specification, and execute a
fresh exact-HEAD archive proof. Those later transitions are not work that this
archived checklist claims was already complete. Candidate land, accepted-root
closeout, local publish readiness, and remote publication require their own
later current receipts. Remote/GitLab publication is independent and
non-blocking.

This change authorizes and tests the mechanism. It does not authorize a real
foreign-lane deletion. A real ownerless effect still requires a separately
selected exact target, accepted decision/Chronicle, irreversible confirmation,
fresh WCP admission, and current postconditions.
