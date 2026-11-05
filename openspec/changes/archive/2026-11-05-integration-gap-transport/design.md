# Design

## Context

See [proposal.md](proposal.md). `refusal(*gaps)` returns an `OutcomeError`, a `ValueError` whose
message is the leading gap and whose outcome carries every gap. So callers and tests that match the
leading gap keep working.

## Goals / Non-Goals

Goals:

- Every refusal in `src/` carries all of its gaps, as the architecture test requires.

Non-goals:

- Any change to which messages are refused.

## Decisions

- **Use the existing refusal.** The identity refusal two lines below already raises
  `refusal(*gaps)`, so the message refusal uses the same form. No new helper.

## Risks / Trade-offs

- None beyond the integration: a later merge of a lane based before `a984a18c4` can bring the old
  pattern back, and the architecture test catches it in that lane's proof.
