# Design

## Context

The decisions behind these tasks are recorded in the archived design of `proof-throughput` (`openspec/changes/archive/2026-10-17-proof-throughput/design.md`). This Change keeps only the decisions needed to finish them.

## Goals / Non-Goals

**Goals:**

- Finish tasks 9.9 against their original acceptance conditions.

**Non-Goals:**

- Weakening an acceptance condition, completing a task by archiving it, or adding obligations outside this outcome.

## Decisions

- **Preserve task identity and acceptance.** Keep stable identities cited by commits, Attestations and peers; recover the remaining obligations from both parents and keep execution evidence by reference rather than in the checklist.
- **Preserve the removed Publisher duty.** Task 9.9.4 retains its completed removal; ETHOS does not acquire architecture rendering or external Publisher Provider acceptance.
- **Carry no requirement delta.** The requirements were accepted when `proof-throughput` archived; restating them here would create a second authority.

## Risks / Trade-offs

- [An accepted requirement is specified before its implementation task closes] → The open task in this Change names the remaining work, and proof of this Change cannot pass until its tasks are complete.
- [A lane still edits `proof-throughput`] → That lane moves its edits to the successor named here when it next refreshes onto dev.
