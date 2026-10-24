# Design

## Context

The decisions behind these tasks are recorded in the archived design of `proof-throughput` (`openspec/changes/archive/2026-10-17-proof-throughput/design.md`). This Change keeps only the decisions needed to finish them.

## Goals / Non-Goals

**Goals:**

- Finish tasks 13.2, 13.3 against their original acceptance conditions.

**Non-Goals:**

- Weakening an acceptance condition, completing a task by archiving it, or adding obligations outside this outcome.

## Decisions

- **Move tasks verbatim with their original identities.** Renumbering was rejected, because commits, Attestations and peer threads already cite these identities.
- **Carry no requirement delta.** The requirements were accepted when `proof-throughput` archived; restating them here would create a second authority.
- **Close on the delivered scope.** On 2026-10-24 [DR-0016](../../../../docs/decisions/dr-0016-change-closure-scope.md) withdrew the tasks that this Change did not deliver from 0.2.0. Each withdrawn task keeps its line in `tasks.md` without a checkbox and returns through a new Change; the goals above describe the original scope.

## Risks / Trade-offs

- [An accepted requirement is specified before its implementation task closes] → The open task in this Change names the remaining work, and proof of this Change cannot pass until its tasks are complete.
- [A lane still edits `proof-throughput`] → That lane moves its edits to the successor named here when it next refreshes onto dev.
