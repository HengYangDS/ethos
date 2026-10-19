# Design

## Context

The decisions behind these tasks are recorded in the archived design of `proof-throughput` (`openspec/changes/archive/2026-10-17-proof-throughput/design.md`). This Change keeps only the decisions needed to finish them.

## Goals / Non-Goals

**Goals:**

- Finish tasks 13.4 against their original acceptance conditions, including the relocated 13.4.7 and 13.4.8.

**Non-Goals:**

- Weakening an acceptance condition, completing a task by archiving it, or adding obligations outside this outcome.

## Decisions

- **Move tasks verbatim with their original identities.** Renumbering was rejected, because commits, Attestations and peer threads already cite these identities.
- **Carry only the deltas that lanes implemented against `proof-throughput` before it archived.** Its accepted requirements are not restated. The two integrated lanes implemented explicit maintenance bases for lane start (13.4.7) and configurable peer names (13.4.8) while editing `proof-throughput`; those edits move here as one MODIFIED and one ADDED requirement, because an archived Change stays immutable.

## Risks / Trade-offs

- [An accepted requirement is specified before its implementation task closes] → The open task in this Change names the remaining work, and proof of this Change cannot pass until its tasks are complete.
- [A lane still edits `proof-throughput`] → That lane moves its edits to the successor named here when it next refreshes onto dev.
