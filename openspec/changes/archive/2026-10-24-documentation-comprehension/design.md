# Design

## Context

The decisions behind these tasks are recorded in the archived design of `proof-throughput` (`openspec/changes/archive/2026-10-17-proof-throughput/design.md`). This Change keeps only the decisions needed to finish them.

## Goals / Non-Goals

**Goals:**

- Finish tasks 12.1, 12.3, 12.4, 12.5, 12.6 against their original acceptance conditions.
- Carry the unaccepted reader-route and decision-carrier increments through task 12.3.2 and the active `repository-governance` delta.

**Non-Goals:**

- Weakening an acceptance condition, completing a task by archiving it, or adding obligations outside this outcome.

## Decisions

- **Move tasks verbatim with their original identities.** Renumbering was rejected, because commits, Attestations and peer threads already cite these identities.
- **Keep accepted history unchanged.** Restore the archived governance artifact exactly from the incoming accepted source. The three local, unaccepted scenarios belong in this active Change, not the historical archive.
- **Use complete MODIFIED blocks.** Preserve every accepted scenario in `Native Documentation Topology` and `Minimal Decision Rationale Preservation`; the delta adds only the declared reader-route and decision-carrier increments.
- **Reuse the shared documentation owner.** The Docs Registry validates selected-source membership, readable confined inputs, reader routes and decision carriers. Native consumers exercise the same implementation; no adopter-local tool or second registry is introduced.
- **Close on the delivered scope.** On 2026-10-24 [DR-0016](../../../../docs/decisions/dr-0016-change-closure-scope.md) withdrew the tasks that this Change did not deliver from 0.2.0. Each withdrawn task keeps its line in `tasks.md` without a checkbox and returns through a new Change; the goals above describe the original scope.

## Risks / Trade-offs

- [A merge makes local scenarios appear historically accepted] → Preserve archive bytes and qualify the active delta through native validation, exact proof and installed ETHOS/DDWG consumers.
- [An accepted requirement is specified before its implementation task closes] → The open task in this Change names the remaining work, and proof of this Change cannot pass until its tasks are complete.
- [A lane still edits `proof-throughput`] → That lane moves its edits to the successor named here when it next refreshes onto dev.

## Migration Plan

Restore the accepted archive, move task 12.3.2 and the complete delta here, and validate native task identities, hierarchy, official OpenSpec and original formatting. Qualify the installed common owner on ETHOS and the unchanged DDWG consumer before retiring DDWG duplicates.
