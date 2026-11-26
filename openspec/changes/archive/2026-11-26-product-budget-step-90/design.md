# Design

## Context

See the [proposal](proposal.md) and DR-0036, the decision record that task 1.1 of this Change
writes. DR-0025 took the previous product step. The ceilings were read on 2026-11-24 at accepted
`dev` and at the lane's head; the two searches were run on accepted `dev` that day.

## Goals / Non-Goals

Goals:

- One 5,000 step for the product, with its decision, its late review and its removal recorded as
  they happened.

Non-Goals:

- A tests or tools step. The tests stand past the revisit point of DR-0033, and that review is a
  decision of its own.
- Compressing or relabeling code, and the structural reductions that DR-0020 and DR-0025 gave to
  0.3.0.
- The work that the space is for.

## Decisions

1. **The record states the order as it was.**
   - **Rests on:** the owner's decision of 2026-11-24, taken on a report that said the review had
     not been made.
   - **Considered:** writing the record in the usual order, review first.
   - **Chosen because:** the record preserves what happened; DR-0010 and the rule of 2026-11-01
     stand for the next step.
   - **Applies to:** DR-0036's title, its decision and its consequences.
2. **The one removal lands with the step.**
   - **Rests on:** a search of every tracked file outside the archive for each top-level name of
     the product: one name is found once, at its definition.
   - **Considered:** leaving a single line in place.
   - **Chosen because:** the review's finding is acted on, however small.
   - **Applies to:** `src/ethos/contracts/semantic.py`. It drops no behavior: nothing raises the
     code.
3. **One step of 5,000, alone and first.**
   - **Rests on:** DR-0010's rule of one step, and DR-0028's finding on a step inside a row.
   - **Considered:** the step inside the first Change that needs it.
   - **Chosen because:** a step inside a row puts the budget decision in that row.
   - **Applies to:** the product ceiling only, from 85,000 to 90,000.

## Risks / Trade-offs

- A step taken before its review can become the habit. DR-0036 says that it was once, and the
  next step's review is due at 88,000.

## Migration Plan

None. Reverting the commit restores 85,000; readiness then refuses any head above it.
