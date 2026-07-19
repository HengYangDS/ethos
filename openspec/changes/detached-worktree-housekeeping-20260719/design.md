## Context

Git is authoritative for linked-worktree registration. ETHOS already governs
Work Lane ownership and retirement, but detached host-created worktrees are not
necessarily Work Lanes and therefore need a separate, narrower cleanup path.
The path must remove only mechanically safe temporary residue and must not turn
absence of a branch into permission to discard content.

## Design

The adapter reads `git worktree list --porcelain` and emits one entry per
registered worktree. Classification is deliberately ordered and fail-closed:

1. a branch-bound entry is protected;
2. a Git-locked entry is protected;
3. the audited checkout is protected;
4. a missing, unreadable, or dirty entry is protected;
5. a detached clean entry outside controlled temporary roots is protected;
6. only the remaining detached clean temporary entry is removable.

The default controlled roots are the active session temporary directory, the
system `/tmp` real path, and the current Codex home `worktrees` directory. The
explicit system root matters on macOS, where `$TMPDIR` and `/private/tmp` are
different trees. Tests inject a temporary root so classification is
deterministic. Apply mode requires `--authorize`,
re-inventories each selected path, and invokes ordinary `git worktree remove`
without force. A changed candidate or failed removal produces a blocking gap.
A failed Git inventory blocks the command rather than projecting an empty clean
state.

## Alternatives

- **Delete every detached worktree:** rejected because detached recovery and
  semantic checkouts can contain unique work.
- **Use `git worktree prune` only:** rejected because prune handles missing
  administrative records, not existing clean temporary directories.
- **Treat detached worktrees as Work Lanes:** rejected because this would invent
  ownership and lease authority that Git topology does not provide.

## Verification

- Adapter tests cover clean, dirty, unreadable, branch-bound, outside-root,
  locked, failed inventory, missing authorization, recheck, and removal
  behavior.
- CLI tests cover dry-run, blocked apply, authorized apply, and command registry
  discovery.
- OpenSpec, command registry, focused quality, and HEAD-bound proof remain
  required before land.
