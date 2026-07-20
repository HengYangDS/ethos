## 1. Continuation admission

- [x] 1.1 Preserve the archived initial carrier and bind its claim to this
  active continuation.
- [x] 1.2 Record the live candidate and current shared submit tip without
  asserting remote or hosted completion.

## 2. Local convergence

- [x] 2.1 Refresh the owned lane from the current candidate and re-observe
  protected and submit refs immediately before merge.
- [x] 2.2 Merge the current submit tip with an ordinary merge, then refresh
  parity and execute a HEAD-bound proof.
- [x] 2.3 Archive this carrier after its documented local implementation stage;
  the archive-transition head requires a fresh executed proof before candidate land.

## 3. Post-archive operational boundary

The archive does not pre-certify any later effect.  After archive proof, the
same owner performs candidate/accepted closeout, read-only identity-policy
review, per-ref no-force push dry-runs and updates, per-ref submit deletion
dry-runs and deletions only when accepted ancestry holds, and distinct remote
and hosted observations.  Those external-state steps remain runtime facts, not
unchecked source-implementation tasks in this completed carrier.
