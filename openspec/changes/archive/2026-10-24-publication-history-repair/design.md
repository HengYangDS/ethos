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
- **Retire a redundant projection by retention as well as by acceptance.** A proposal whose tip dev never absorbed is redundant once its review is closed and an owned Work Lane still reaches the tip, or the same peer keeps it at the closed review's own ref (`refs/pull/<n>/head`, `refs/merge-requests/<iid>/head`). Deleting the projection then loses no object, which is the exact preservation 13.4.3 requires before retiring obsolete proposals (issue #12; PR #13's branch). A candidate ref does not retain it, because landing resets the candidate to accepted dev; the product contract already refuses candidate refs as retained topics. Patch equivalence, matching names and unobserved provider state still preserve the proposal.
- **Close on the delivered scope.** On 2026-10-24 [DR-0016](../../../../docs/decisions/dr-0016-change-closure-scope.md) withdrew the tasks that this Change did not deliver from 0.2.0. Each withdrawn task keeps its line in `tasks.md` without a checkbox and returns through a new Change; the goals above describe the original scope.

## Risks / Trade-offs

- [An accepted requirement is specified before its implementation task closes] → The open task in this Change names the remaining work, and proof of this Change cannot pass until its tasks are complete.
- [A local retainer is retired after its projection] → Lane retirement removes a Work Lane only when dev absorbed its commits or another topic ref retains them, so the retained tip stays reachable; the projection's deletion relied on the retention observed when it was admitted.
- [A lane still edits `proof-throughput`] → That lane moves its edits to the successor named here when it next refreshes onto dev.
