## 1. Admission and contract

- [x] 1.1 Create the OpenSpec carrier and bind its optionality, external control
  plane, physical extension boundary, and no-account/no-daemon constraint.
- [x] 1.2 Obtain owner-authorized source-budget admission for the bounded
  `python_other` and test allowance; preserve the global hard cap.
- [x] 1.3 Add the adapter requirement delta and validate the carrier.

## 2. Provider-local generic Git adapter

- [x] 2.1 Implement the default-off generic Git pre-receive adapter under the
  independent-verification extension, with one fixed Git tree lookup and no
  client-controlled command execution.
- [x] 2.2 Validate protected provider configuration, exact receipt storage,
  payload digest, signature, proposed commit/tree, remote, action, policy, and
  proof-floor bindings.
- [x] 2.3 Add focused tests for disabled mode, unprotected refs, valid protected
  updates, deletion, stale/invalid receipts, policy/floor/tree mismatch, and
  physical placement.

## 3. Proof and closeout

- [x] 3.1 Validate OpenSpec, source budget, extension tests, and the selected
  adapter quality gates.
- [ ] 3.2 Run a fresh HEAD-bound proof, archive the carrier, land through the
  candidate, and stop before remote publication.
