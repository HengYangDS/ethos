# Design

## Context

The decisions behind these tasks are recorded in the archived design of `proof-throughput` (`openspec/changes/archive/2026-10-17-proof-throughput/design.md`). This Change keeps only the decisions needed to finish them.

## Goals / Non-Goals

**Goals:**

- Finish tasks 8.9, 8.10, 8.11, 8.12, 8.13, 10.4, 10.6, 10.7, 10.11, 10.12, 10.13, 11.9 against their original acceptance conditions.
- Finish task 10.14, the installed and cold-platform qualification of the shared `ethos lane format` and `source-format` owners that the integrated lanes delivered.

**Non-Goals:**

- Weakening an acceptance condition, completing a task by archiving it, or adding obligations outside this outcome.

## Decisions

- **Move tasks verbatim with their original identities.** Renumbering was rejected, because commits, Attestations and peer threads already cite these identities.
- **Carry no requirement delta, except for a task no accepted requirement covers.** The requirements were accepted when `proof-throughput` archived; restating them here would create a second authority. Task 11.9.2.9 is the exception: no accepted requirement requires complete UTF-8 authored text before formatter selection, so this Change adds that requirement to `repository-paradigm`. The judgement combines Git's content classification with complete UTF-8 decoding and NUL refusal, before narrowing inputs to native formatters. The native format declarations select text and canonical carriers; binary, received, generated and immutable owners remain preserved. Checkout attributes do not decide validity; issue #16 showed both a valid `-text` refusal and unobserved plain-text carriers.
- **Close on the delivered scope.** On 2026-10-24 [DR-0016](../../../docs/decisions/dr-0016-change-closure-scope.md) withdrew the tasks that this Change did not deliver from 0.2.0. Each withdrawn task keeps its line in `tasks.md` without a checkbox and returns through a new Change; the goals above describe the original scope.

## Risks / Trade-offs

- [An accepted requirement is specified before its implementation task closes] → The open task in this Change names the remaining work, and proof of this Change cannot pass until its tasks are complete.
- [A lane still edits `proof-throughput`] → That lane moves its edits to the successor named here when it next refreshes onto dev.
