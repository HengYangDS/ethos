## 1. Bound the recovery

- [x] 1.1 Add the narrow lifecycle/recovery request and deterministic admission
  reduction while preserving normal dirty accepted-root refusal.
- [x] 1.2 Bind receipt, Git-state, lock-fingerprint, atomic no-replace
  quarantine, and postcondition validation without ref/lease/proof/SQLite
  effects.
- [x] 1.3 Route the public closeout CLI flags and document the runner-version
  boundary.

## 2. Prove failure boundaries

- [x] 2.1 Cover wrong receipt/head, missing authorization/confirmations,
  arbitrary dirty content, lock drift/type/digest mismatch, unsafe quarantine,
  target race, sync failure, and post-sync drift.
- [x] 2.2 Cover valid recovery where the candidate runner is a descendant of
  the already-promoted accepted head and the only removed source path is the
  verified stale lock.
- [x] 2.3 Assert that recovery imports neither retired-resolution code nor
  SQLite/state storage and introduces no initializer façade.

## 3. Complete local closeout

- [ ] 3.1 Validate OpenSpec, Claim, focused gates, full executed HEAD-bound
  proof, and parity.
- [ ] 3.2 Land to candidate and run the candidate runner against the original
  accepted-root failure receipt.
- [ ] 3.3 Verify normal accepted-root closeout/current state, local publish
  readiness, native lane retirement, and bounded housekeeping without push.
