# Proposal

## Why

`proof-throughput` grew to 200 tasks and a 2,959-line design, so it can no longer be read, proved or archived as one Change. Its requirements are accepted when it archives to `openspec/changes/archive/2026-10-17-proof-throughput`; this Change carries its open implementation obligations 7.3, 7.4, 7.5, 7.9, 7.11, 7.12, 7.13 for one cohesive outcome, and `repository-paradigm`'s task 3.8, the GitLab acceptance of the CI supply image. Qualify one hosted execution path per Forge: supply failure reporting, single execution, rootless providers, CUE-generated projections, job partitions and runner capacity.

## What Changes

- Continue the listed tasks with their original identities, states, acceptance conditions, dependencies and evidence references, moved verbatim.
- Add no requirement. Each task implements a requirement already accepted through `proof-throughput`, or through `repository-paradigm` for 3.8.
- Modify the accepted requirement that one test attempt provides reconstructable reports where task 7.4.1 changed the link observation: a 503 from an upstream link is temporary unavailability rather than a broken link, and a Lychee diagnostic on stderr fails the observation.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: the external-link observation accepts a 503 as temporary unavailability and fails on any Lychee diagnostic.

## Impact

Code, tests and evidence owned by these tasks. Original execution history remains in Git, in the archived design of `proof-throughput`, and with its native evidence owners.
