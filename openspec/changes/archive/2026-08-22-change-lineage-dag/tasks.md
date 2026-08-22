## 1. Contract And RED

- [x] 1.1 Add strict capability deltas for immutable DAG lineage, exact-tree
  resolution, public predecessor input, and recovery identity.
- [x] 1.2 Add a public `start-change` join test proving the current parent plus
  additional predecessors are emitted as one canonical set.
- [x] 1.3 Replace the fresh-lane singleton rejection test with valid historical
  predecessor and unresolved-before-effect tests.
- [x] 1.4 Add retry/recovery coverage proving predecessor-set drift cannot be
  recognized or applied.

## 2. Unique Owner Replacement

- [x] 2.1 Add exact-tree Commitment digest resolution to one OpenSpec
  `change_lineage` observation owner without a cache, index, or history ledger;
  reuse Commitment's canonical digest-set invariant and delete the redundant
  `contracts.change_lineage` owner.
- [x] 2.2 Extend the public `start-change` command with repeatable predecessor
  input and mandatorily include the current Lease-bound Commitment.
- [x] 2.3 Admit fresh lane Commitments only after every predecessor resolves in
  the exact base tree before ref, worktree, or Lease mutation.
- [x] 2.4 Bind the complete predecessor set through prepared request, recovery,
  effect, and Attestation checks.
- [x] 2.5 Delete singleton-only parameters, equality checks, gap vocabulary, and
  obsolete tests; prove repository-wide reference closure.

## 3. Validation And Closeout

- [x] 3.1 Run strict OpenSpec validation plus focused Ruff, type, architecture,
  fresh-lane, rollover, recovery, and generation tests.
- [x] 3.2 Run the complete applicable proof and verify current HEAD/tree and
  artifacts.
- [x] 3.3 Archive through the public lifecycle, rerun required post-archive
  proof, land exact CAS, project the accepted runtime, and retire this lane.
