## Why

On July 26, 2026, native accepted-root closeout advanced the accepted ref to a
proven candidate SHA but failed while synchronizing the accepted checkout after
an index lock remained. Normal closeout correctly refuses the resulting dirty
accepted root. Without a narrow recovery path, that already-promoted checkout
cannot be repaired through the public command plane.

## What Changes

- Add one explicit `ethos land --closeout --recover-accepted-worktree-sync`
  mode. It is not a generic dirty-root bypass and it never advances a ref.
- Bind recovery to the exact external failed-closeout receipt, its SHA-256, the
  already-promoted accepted head, the prior accepted tree represented by the
  index, and the exact stale-lock digest and fingerprint.
- Relocate only that lock with an OS-backed atomic no-replace rename into an
  absent external, same-filesystem quarantine path. Unsupported platforms and
  target races fail closed.
- Permit the candidate runner to be the promoted head or a later descendant so
  newly landed recovery code can repair an earlier accepted-worktree residue;
  the accepted checkout and accepted ref must still equal the receipt's exact
  promoted head.
- Keep ordinary `land --closeout` unchanged: arbitrary dirty accepted roots,
  ref movement, leases, proof state, SQLite, and retired-resolution state remain
  outside recovery.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=accepted-closeout-worktree-recovery; reuse=extend; change=modify; facet:lifecycle=closeout,recovery; facet:surface=cli,contract,adapter,test,docs; facet:authority=source,test,openspec,evidence

## Impact

- Closeout lifecycle contract, mutation adapter, and public `land` CLI.
- Closeout, kernel, architecture, and failure-boundary tests.
- Runner/mutation and command-plane documentation.

## Out Of Scope

- Retrying ordinary closeout, changing `dev`, `candidate/dev`, `main`, a lease,
  a proof record, or local SQLite state.
- Recovering arbitrary user changes, foreign worktrees, retired-resolution
  records, or a lock whose receipt, digest, identity, or quarantine binding
  differs.
- Remote publication, GitLab access, or unrelated work-lane housekeeping.
