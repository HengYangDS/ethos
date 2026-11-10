# Design

## Context

See the [proposal](proposal.md). The session already prints its payload on stdout when it
completes (`tools/ci/dependency_audit.py`, the end of `_run`), and the gate runner reads that
stdout through `captured_dependency_acceptance` (`src/ethos/adapters/gates/runner.py`).

## Goals / Non-Goals

Goals: every dependency audit refusal names a fixed gap.

Non-Goals: retrying on contention, and running gates concurrently on one lane.

## Decisions

1. The refusal payload uses the existing payload's keys, so one reader handles both.
2. A JSON parse failure becomes `dependency_audit_payload_missing`, raised from the parse error so
   the cause stays attached.
3. A refusal carries every gap of its `required_gaps` (validated as non-empty strings, else
   `dependency_audit_refused`) through `ethos.contracts.outcome.refusal`, and the decision keeps
   them all in `required_gaps` beside the leading `reason`.

## Risks / Trade-offs

None beyond a few lines in three product and tool files: the session, the captured reader and
the gate runner, which with the proof reader now takes every gap through `decision_gaps`.
