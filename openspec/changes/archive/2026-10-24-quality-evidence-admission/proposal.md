# Proposal

## Why

`proof-throughput` grew to 200 tasks and a 2,959-line design, so it can no longer be read, proved or archived as one Change. Its requirements are accepted when it archives to `openspec/changes/archive/2026-10-17-proof-throughput`; this Change carries its open implementation obligations 8.9, 8.10, 8.11, 8.12, 8.13, 10.4, 10.6, 10.7, 10.11, 10.12, 10.13, 11.9, plus installed formatting qualification 10.14, for one cohesive outcome. Admit only complete quality evidence: hosted result and report integrity, native quality rules, early failure, and declaration-to-consumer wiring of the shared quality floor.

## What Changes

- Continue the listed tasks with their original identities, states, acceptance conditions, dependencies and evidence references, moved verbatim.
- Add one requirement, for task 11.9.2.9: authored text is complete UTF-8 without NUL, including declared plain-text and canonical carriers before formatter selection. Every other task implements a requirement already accepted through `proof-throughput`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-paradigm`: authored text is valid text (11.9.2.9). The behavior of the other tasks is specified by the accepted specifications.

## Impact

Code, tests and evidence owned by these tasks. Original execution history remains in Git, in the archived design of `proof-throughput`, and with its native evidence owners.
