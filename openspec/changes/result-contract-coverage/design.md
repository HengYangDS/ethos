# Design

## Context

See [proposal.md](proposal.md). The coverage floor is the measuring run's own decision, so a gap
under it is closed by specifying behavior that exists, never by lowering the floor.

## Goals / Non-Goals

Goals:

- Every refusal the result contract added is specified by a test.

Non-goals:

- Any change to `ethos.result`, `ethos.contracts.next_step` or `ethos.surface.cli.output`.

## Decisions

- **Test through the public readers.** Each test builds the input it refuses and expects the
  documented outcome: an inline result with `detail_unavailable`, `result_detail_mismatch`, or an
  instruction instead of a command.

## Risks / Trade-offs

- The repository's combined coverage stays close to its floor; widening that margin is separate
  work.
