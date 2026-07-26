## Context

The native closeout effect advances the accepted ref before it synchronizes the
accepted checkout. A stale `index.lock` can therefore make the second action
fail after promotion. The observed residue is precise: `HEAD` and `dev` equal
the receipt's promoted SHA; the index and worktree equal the prior accepted
tree; there is no untracked or conflicted content; and the receipt records
`accepted_worktree_sync_failed`.

Normal closeout must keep refusing arbitrary dirty accepted roots. A generic
retry or reset would erase legitimate work and make the boundary bypassable.

## Decisions

1. **Explicit recovery command.**
   `--recover-accepted-worktree-sync` requires `--closeout`, the external
   failed-closeout receipt, both SHA-256 bindings, an external quarantine path,
   authorization, stale-lock confirmation, irreversible confirmation, and
   `--expect-head` for the already-promoted accepted SHA. Dry-run and apply
   both repeat admission.
2. **Receipt-bound residue.**
   The receipt must identify the configured accepted/candidate branches and
   `accepted_worktree_sync_failed`. The accepted checkout's `HEAD` and accepted
   ref must still equal its promoted SHA; its index/worktree must still equal
   the receipt's prior tree with no untracked or conflicted content.
3. **Candidate runner is a versioned executor, not recovery truth.**
   The configured candidate ref may equal the promoted SHA or be its descendant.
   This permits a later candidate runner to contain the recovery controller
   while accepted remains at the interrupted promotion. A divergent or missing
   candidate blocks; recovery never rewrites candidate or accepted refs.
4. **Atomic no-replace forensic relocation.**
   Recovery validates a regular, non-symlink lock and an absent external
   same-filesystem destination, then uses Darwin `renameatx_np(RENAME_EXCL)` or
   Linux `renameat2(RENAME_NOREPLACE)`. The operation moves the source without
   a check-then-overwrite window; unavailable primitives, target races, digest
   drift, or post-move identity mismatch block. The implementation does not
   fall back to `os.replace`, `os.rename`, link-plus-unlink, or deletion.
5. **No new authority plane.**
   The recovery stays in the existing closeout module, reuses its worktree-sync
   primitive, and imports neither retired-resolution code nor SQLite/state
   storage. No package initializer or compatibility façade is introduced.

## Failure Handling

- Malformed receipt, receipt digest mismatch, wrong branch/head, non-ancestor
  candidate runner, prior-index mismatch, user work, untracked content,
  conflict, lock type/digest/fingerprint drift, occupied/symlink/cross-device
  quarantine, unavailable atomic primitive, target race, sync failure, ref
  drift, or post-sync dirt blocks the transition.
- A successful quarantine followed by sync failure reports the immutable
  quarantine location. Recovery never restores the lock automatically because
  doing so could recreate stale state over changed Git facts.
- No recovery outcome changes a ref, lease, proof record, SQLite record,
  retired-resolution record, or ownerless-resolution record.

## Validation

1. Cover valid descendant-runner recovery, normal dirty-root refusal, receipt
   and confirmation admission, lock/quarantine failure edges, and no-replace
   race behavior.
2. Assert the recovery controller remains outside retired-resolution and
   state-store dependencies.
3. Validate OpenSpec, Claim, focused gates, an executed HEAD-bound proof,
   parity, candidate land, accepted recovery, normal current closeout, local
   publish readiness, and native lane retirement. Do not push.
