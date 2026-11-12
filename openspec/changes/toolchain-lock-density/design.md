# Design

## Context

See the [proposal](proposal.md). complexipy owns cognitive complexity: a function stays at or below
15 unless the baseline pins its earlier score, and a pinned function that improves must leave the
baseline.

## Goals / Non-Goals

Goals:

- The decision-density test passes with the toolchain rule unchanged.

Non-Goals:

- Any change to which gaps the paradigm reports.

## Decisions

1. `_lock_gaps(config, lock, declared, tracked)` yields the `settings.locked` gap and the lock gap,
   in that order; `toolchain_gaps` delegates to it.
2. The stale pin for `repository_mise_files` is removed, since it now measures 15.

## Risks / Trade-offs

- None: the order and text of the gaps stay the same, and the toolchain tests pin them.
