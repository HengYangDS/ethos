# Design

## Context

See [proposal.md](proposal.md). The coverage floor is the measuring run's own decision, so a gap
under it is closed by testing behavior that exists, not by lowering the floor.

## Goals / Non-Goals

Goals:

- Both refusals of `lock_sidecars` are specified by a test.

Non-goals:

- Any change to `mise_lock.py` or `mise.py`.

## Decisions

- **Test the refusals through the public reader.** `repository_mise_files` is the only caller of
  `lock_sidecars`, so each test writes the lock it refuses and expects the exact refusal.

## Risks / Trade-offs

- The repository's combined coverage stays close to its floor; this Change restores the margin the
  new module took, and widening it is separate work.
