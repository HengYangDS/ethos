# Design

## Context

See [proposal.md](proposal.md). The paradigm caps a source module at 500 effective lines; the cap
asks for semantic consolidation, never a file split for its own sake.

## Goals / Non-Goals

Goals:

- `mise.py` returns under the ceiling along a real seam.

Non-goals:

- Any behavior change.

## Decisions

- **The lock is its own concern.** Reading `mise.lock` (its aube sidecar directories and its
  dependency-graph entries) is pure data parsing over the lock text. It needs neither the native
  executable nor the trust boundary that `mise.py` owns, so it moves to `mise_lock.py` with public
  names, `lock_sidecars` and `graph_locked`.

## Risks / Trade-offs

- None; the toolchain tests cover both readers through `mise.py`.
