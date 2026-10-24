# Proposal

## Why

`proof-throughput` grew to 200 tasks and a 2,959-line design, so it can no longer be read, proved or archived as one Change. Its requirements are accepted when it archives to `openspec/changes/archive/2026-10-17-proof-throughput`; this Change carries its open implementation obligations 13.4 for one cohesive outcome. Close publication provenance after history repair: exact candidate installation, attribution and signature repair, false-coauthor selection and resumption of the conserved product candidate.

## What Changes

- Continue the listed tasks with their original identities, states, acceptance conditions, dependencies and evidence references, moved verbatim.
- Specify two behaviors that integrated lanes implemented against `proof-throughput` before it archived: a Work Lane may start from an explicit trusted immutable accepted base for maintenance, and an explicit publication peer declaration defaults its ID to the provider and its Git remote to the resolved ID. Every other task implements a requirement already accepted through `proof-throughput`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `adapters`: Lease-backed Lane Start admits an explicit trusted immutable base.
- `repository-governance`: publication peer IDs and Git remote names default from their explicit declaration.

## Impact

Code, tests and evidence owned by these tasks. Original execution history remains in Git, in the archived design of `proof-throughput`, and with its native evidence owners.
