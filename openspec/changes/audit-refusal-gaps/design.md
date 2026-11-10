# Design

## Context

See the [proposal](proposal.md). The session already prints its payload on stdout when it
completes (`tools/ci/dependency_audit.py:340`), and the gate runner reads that stdout through
`captured_dependency_acceptance` (`src/ethos/adapters/gates/runner.py:220-226`).

## Goals / Non-Goals

Goals: every dependency audit refusal names a fixed gap.

Non-Goals: retrying on contention, and running gates concurrently on one lane.

## Decisions

1. The refusal payload uses the existing payload's keys, so one reader handles both.
2. A JSON parse failure becomes `dependency_audit_payload_missing`, raised from the parse error so
   the cause stays attached.

## Risks / Trade-offs

None beyond a few lines in two files.
