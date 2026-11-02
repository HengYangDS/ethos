# Design

## Context

See [proposal.md](proposal.md). `archive_readiness_gaps(root, change=, tree=)` archives the Change
on a disposable projection of an exact tree and validates every spec strictly. The proof calls it
on the head it proves; the archive preview checks only the lifecycle and the commitment.

## Goals / Non-Goals

**Goals:**

- A preview that reports `ready_to_archive` means the archive's postimage validates strictly.

**Non-Goals:**

- Changing the apply path, its compensation or the proof's own check.

## Decisions

- **Reuse the proof's check on the head's tree.** One function decides archive readiness for both
  callers, so they cannot disagree.

## Risks / Trade-offs

- [The preview takes longer] → The simulation runs the official CLI on a projection once, about a
  second at ETHOS's size.
