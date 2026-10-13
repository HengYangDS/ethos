## Context

`apply_operation` runs remove_worktree, then delete_ref, then revoke_lease. It re-observes the carriers after every effect and reduces them with `reduce_progress`. That reducer also treated `accepted_state != "expected"` as carrier drift, so an accepted fast-forward after the worktree removal raised before progress could be recorded. The failure path re-observed, raised again, and reported without progress. `_report` then fell back to `recover` for the same receipt.

## Decisions

1. Keep the receipt immutable and keep the exact accepted assertion inside the ref-deletion effect. Recovery never re-plans: the governing rule is that a stale receipt never substitutes for a missing fact.
2. Observe the accepted ref with its own `AcceptedState`. An exact match is `expected`. A fast-forward from the recorded head is `advanced`. A rewrite, a rewind or an absent ref is a carrier-state failure, as before: a receipt whose accepted world was replaced recognizes no progress, and a foreign or synthetic receipt is never mistaken for a terminal retirement. Reduce progress only from the carriers that the operation removes. Treat `advanced` as admission drift before each remaining worktree or ref deletion. Lease revocation alone does not depend on accepted state.
3. Make `continuation.py` the single owner of retirement next actions. It chooses by failure class and current facts:
   - The receipt can still finish, as with contention, transient process failures or an interrupted removal: `recover` for the same receipt.
   - The receipt is invalidated and the worktree is still linked: the same-mode derivation. That is the content review for reviewed abandonment, `landed --branch`, or `abandon --branch`. In every other case it is `ethos lane status`.
   - The receipt is invalidated and the worktree is gone: an unbound route, chosen by accepted ancestry and Lease:
     - `superseded --path --absorbed-by <current accepted>` when the head is absorbed and the Lease is held;
     - `absorbed-ref` when the head is absorbed and there is no Lease;
     - `abandon --branch` when the head diverges and the Lease is held;
     - `ethos lane status` otherwise.
   - Carrier state drifted: `ethos lane status`.
4. Persist progress in the failure path only when applying, so dry-run recovery stays free of writes.

## Risks

- A fresh derivation re-runs current admission. It may block, for example on an expired Lease or on unique commits, and it reports that gap instead of retiring. This is intended fail-closed behavior.
- The continuation reads the accepted ref and ancestry while reporting. If that observation fails, the continuation degrades to `ethos lane status`.
