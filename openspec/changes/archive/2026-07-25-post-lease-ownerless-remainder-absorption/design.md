## Context

The previous semantic-resolution wave correctly protected these lanes while
their leases were valid. On July 25, 2026, fresh status reports missing leases
and Claims for all four. The source set is heterogeneous: two intent/migration
carriers, one native-resolution predecessor, and one dirty compression attempt.
One disposition for the whole set would therefore be unsafe.

## Decisions

### 1. Semantic absorption precedes deletion

Every branch receives an exact target observation and an explicit map of useful
invariants, rejected replay, and current semantic receiver. Clean historical
bytes are not preserved merely because they are old. Dirty staged and unstaged
bytes are preserved before retirement even when product replay is rejected.

### 2. Valid-owner successors remain read-only

The native-resolution successor and terminal-convergence lanes are observed only
to prove that relevant invariants have a current owner. Their worktrees, refs,
leases, Claims, source, tests, and evidence are not mutated, landed, retired, or
used to mint authority.

### 3. Use per-lane native dispositions

- legacy freeze capability: `retire`;
- zero-coupling intent: `retire`;
- dirty ownerless closeout compression: `preserve-retire`;
- native resolution predecessor: `retire`.

Every decision is separate, exact-observation-bound, non-reusable, and blocked
by renewed ownership or drift.

### 4. Keep clear separate

The dirty package is recovery evidence, not product truth. After preservation
and source retirement, a new Work Lane must bind its exact manifest, restate why
no unique product behavior remains, pass proof and accepted closeout, and only
then invoke native clear with irreversible confirmation.

## Risk Controls

- no raw Git worktree or ref deletion;
- no batch decision that hides one lane's identity;
- no trust-bearing claim from the contended historical full-test run;
- exact cached, working, full-index, and status digests for the dirty lane;
- current owner/lease/Claim/path-occupancy recheck immediately before effect;
- GitLab unavailability remains a remote observation boundary, not a local
  closeout blocker.
