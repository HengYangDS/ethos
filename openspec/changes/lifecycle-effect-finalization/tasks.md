## 1. Contract and RED

- [x] 1.1 Add the complete rename+modify delta for lifecycle-effect finalization and preserve every existing archive scenario.
- [x] 1.2 Add RED coverage for official OpenSpec 1.9 archive finalization with empty active changes and canonical/spec/policy projection paths.
- [x] 1.3 Add RED coverage for a signed Change-start commit followed by later in-scope commits while the Lease remains on the archived predecessor.
- [x] 1.4 Add RED coverage for missing, expired same-holder, different-holder, and ownerless finalization states, including zero-effect compensation classification.
- [x] 1.5 Add a regression that a reference-transaction hook cannot re-enter Git maintenance or hang while a ref lock is held.

## 2. Single authority implementation

- [x] 2.1 Make one lifecycle-effect selector bind official OpenSpec result, source Commitment, exact tree/overlay, paths, Lease generation, and terminal Attestation.
- [x] 2.2 Extend start-change recovery to recognize the unique first-parent successor plus later same-scope commits without creating a second commit or invoking OpenSpec again.
- [x] 2.3 Route archive finalization, post-archive closeout, prewrite, status, plan, prove, land, and hooks through the same selected effect scope.
- [x] 2.4 Implement exact-CAS Lease finalization and idempotent terminal Attestation replay; keep different-holder takeover explicit and owner-authorized.
- [x] 2.5 Remove command-specific active-Change fallback and any lock-acquiring hook observation from the affected paths.
- [x] 2.6 Project concise, stable next actions for every finalization state and distinguish mutation, compensation, residue, and zero-effect outcomes.

## 3. Verification

- [x] 3.1 Run focused lifecycle, archive, hook, and receipt regressions with exact effect assertions.
- [x] 3.2 Run `npx openspec validate lifecycle-effect-finalization --strict --json` and `ethos plan --changed --json`.
- [x] 3.3 Execute changed-scope proof and verify no duplicate lifecycle owner, stale symbols, or parallel recovery path remains.
- [x] 3.4 Verify that the completed implementation is ready for the public ETHOS archive and land lifecycle without making those later lifecycle effects implementation tasks.
