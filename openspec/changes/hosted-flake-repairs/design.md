# Design

## Context

See [proposal.md](proposal.md).

- `_materialize_native` publishes "only a complete, version-qualified native payload". It runs
  `supply.verify` on the prepared executable in scratch and then moves each member into the cache
  (`native_supply.py:359-378`). `resolve_native_tool` later checks only the cached bytes.
- `hold_worktree_refs` computes its deadline before it prepares the transaction and arms a timer
  of the same length over preparation (`worktree_effects.py:73-147`).
- The inventory memo reuses a digest while device, inode, size, mode, mtime and ctime are
  unchanged, and records nothing changed within `_RACY_NS`, 2 seconds, so a later write always
  stamps a different ctime (`inventory_memo.py:1-68`). The test fixture sets `_RACY_NS = 0`.

## Goals / Non-Goals

**Goals:**

- A Windows materialization survives the brief hold that follows running a just-prepared
  executable, without publishing an unqualified one.
- Each of the two tests proves its stated property on any supported host and under proof load.

**Non-Goals:**

- Faster preparation of reference transactions, or a different memo key.
- The DDWG GitLab Windows ARM64 launcher exit 6, which has no root cause yet.

## Decisions

- **Retry the move, not the order.**
  - Qualifying the executable in place after publication would avoid the move, but a failed
    qualification would leave authentic, unqualified bytes that `resolve_native_tool` accepts on
    its next call. A version mismatch could then run silently.
  - Copying the executable to qualify it instead would leave the run copy for scratch cleanup to
    fail on.
  - So publication keeps its order, and on Windows only a `PermissionError` from the move is
    retried, every 100 ms for at most 5 seconds. A refusal that persists still raises.
- **Deadline from entry.** The deadline is computed before preparation, so a hold that waits the
  whole deadline plus a margin after it is entered always outlasts it, whatever preparation took.
  5 seconds leaves preparation more than twice the time it was seen to exceed.
- **Wait for the clock, not a fixed sleep.** The memo test polls a probe file outside the payload
  until its ctime exceeds the recorded ctime, bounded at 5 seconds. A fixed sleep would assume one
  host's timestamp granularity.

## Risks / Trade-offs

- [A Windows refusal that is not transient now takes 5 seconds longer to report] → It still raises
  the original `PermissionError`, inside the materialization's own bound.
- [The ref-holder test takes about 5 seconds instead of 2] → It runs in parallel with other tests
  under the suite's scheduler.
