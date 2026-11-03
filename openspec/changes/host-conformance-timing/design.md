# Design

## Context

See [proposal.md](proposal.md). The package acceptance creates `smoke.events.jsonl` before its
first stage and appends a line when each stage starts and ends, under the claim
`execution_timing_only`. The GitHub job uploads its receipt with `if: always()`, and the GitLab job
declares its artifacts with `when: always`.

## Goals / Non-Goals

**Goals:**

- Every hosted host conformance run retains its stage timings, passing or failing.

**Non-Goals:**

- Changing what the acceptance runs, its platforms or the `windows-11-arm` leg.
- Making the timings proof or release evidence.

## Decisions

- **The events travel in the receipt's artifact.** Both files go to each leg's existing artifact,
  so one download holds the receipt and the timings it names. GitHub keeps
  `if-no-files-found: error`, which fails only when neither file exists.

## Risks / Trade-offs

- [Each artifact grows by the events file] → A local acceptance wrote 199 lines, about 48 KB.
