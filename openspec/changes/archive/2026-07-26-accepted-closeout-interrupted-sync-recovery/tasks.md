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

## 3. Post-archive terminal acceptance (external evidence)

The official archive changes the final canonical-specification HEAD. Executed
proof, candidate land, receipt-bound accepted-root recovery, normal closeout,
local publish readiness, and retirement must therefore run **after** archive
against that exact final HEAD. They are operational acceptance conditions, not
archive-gated implementation checkboxes: marking them here before the archive
exists would be false, while leaving them unchecked would make the historical
carrier's incomplete state visible to archive closeout review.

The post-archive run must preserve command JSON outside the product tree and
perform, in order:

1. strict archive/Claim verification, focused gates, parity, and one executed
   HEAD-bound proof;
2. candidate land and the candidate runner's exact receipt-bound recovery of
   the original accepted-root residue;
3. normal accepted closeout with its candidate-external control receipt, local
   publish readiness without push, native retirement of this lane, and bounded
   housekeeping.
