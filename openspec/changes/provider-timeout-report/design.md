# Design

## Context

See [proposal.md](proposal.md). A provider that times out inside its own command already keeps the
child's streams, because the process layer attaches them to the `TimeoutExpired` it raises, and
`command_outcome` copies them into the diagnostic. Only a provider that returns after the deadline
loses its report.

## Goals / Non-Goals

Goals:

- A late provider's report reaches the gate's result unchanged.

Non-goals:

- Admitting a late result. The deadline is the gate's contract, so a late report decides nothing.

## Decisions

- **Keep, but do not decide.** After the provider returns, an expired deadline appends the
  provider's report as returned, records the verdict as unknown, and adds the timeout diagnostic.
  The deadline check before the provider runs is unchanged: with no time left, nothing runs and
  nothing is reported.

## Risks / Trade-offs

- A late report may itself say `pass`. The gate's verdict stays unknown, and the report is
  evidence of what the provider saw, not a decision.
