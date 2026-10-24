# Design

## Context

The decisions behind these tasks are recorded in the design of `repository-paradigm`: decision 7 fixes YAML front matter as the documentation metadata encoding, and decision 6 fixes the branch role names that the legacy role migration renames into. This Change keeps only the decisions needed to finish the tasks.

## Goals / Non-Goals

**Goals:**

- Finish tasks 2.16, 2.21 and 2.19 against their original acceptance conditions once their adopters release them.

**Non-Goals:**

- Migrating data-department-work-guidelines or di-effect. Each migrates through its own Change; di-effect stays deferred under the workstation rule.
- Weakening an acceptance condition, completing a task by archiving it, or adding obligations outside this outcome.

## Decisions

- **Move tasks verbatim with their original identities.** Renumbering was rejected, because commits and peer threads already cite these identities.
- **Carry no requirement delta.** The requirements are accepted when `repository-paradigm` archives; restating them here would create a second authority.
- **Retire a compatibility reader only after its last adopter migrates.** A reader retired earlier would turn an adopter's accepted documents or refs into gaps before its own Change repairs them.
- **Close on the delivered scope.** On 2026-10-24 [DR-0016](../../../docs/decisions/dr-0016-change-closure-scope.md) withdrew the tasks that this Change did not deliver from 0.2.0. Each withdrawn task keeps its line in `tasks.md` without a checkbox and returns through a new Change; the goals above describe the original scope.

## Risks / Trade-offs

- [The archived documentation metadata scenario precedes its reader] → Until 2.16 lands, the registry still reads a comment-wrapped document, while the repository paradigm reports the wrapper with its repair.
- [An adopter migrates without notice] → Each task's acceptance re-reads every governed repository's accepted head before the retirement lands.
