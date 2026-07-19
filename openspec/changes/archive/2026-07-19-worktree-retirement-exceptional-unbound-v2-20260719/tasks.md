## 1. Native exceptional route

- [x] 1.1 Extend the unbound retirement adapter with accepted-Chronicle,
  exact-target, lease, worktree, protected-ref, and control admission.
- [x] 1.2 Implement pre-effect and post-effect reobservation, compare-and-delete
  ref mutation, and no-clobber attempt and receipt records.
- [x] 1.3 Extend the CLI contract and canonical command documentation without
  adding a host-specific or raw-Git fallback surface.

## 2. Regression coverage

- [x] 2.1 Cover ready dry-run, all control gaps, target mismatch, active lease,
  linked worktree, unaccepted Chronicle, target-specific Chronicle mismatch, and
  exact successful retirement.
- [x] 2.2 Cover pre-effect and post-effect drift plus durable record collisions
  and failures.

## 3. Closeout

- [x] 3.1 Run focused tests and quality checks; update the task state only after
  current evidence exists. The focused retirement and CLI suite passes (`44
  passed`) and the owner Python lint gate passes at the current ratchet floor.
- [x] 3.2 Refresh parity, run strict OpenSpec and head-bound proof, archive,
  and repair the archived-claim carrier binding. Candidate land, accepted
  closeout, and separate native retirement receipts remain governed lifecycle
  transitions after this carrier archive.
  Correct only an observed shared quality-audit catalog drift when it blocks this
  lane's required quality-audit gate; preserve the tool catalog as the SSOT.
