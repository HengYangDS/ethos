# Design

## Context

See the [proposal](proposal.md). Each failing wait is a fixed bound in test code; the product's own
deadlines already come from `seconds()`.

## Goals / Non-Goals

Goals:

- A loaded host does not fail a wait that would complete.

Non-Goals:

- Any change to the product's cancellation, process-group handling or workflow gate.

## Decisions

1. The handshake listener's timeout and the workflow test's `run_command` bound become
   `seconds("tool")`; the child's local connect and the receive after it keep their short bounds,
   since they follow an answer that has already arrived.

## Risks / Trade-offs

- A truly deadlocked child now holds its test for the tool deadline instead of ten or thirty
  seconds; the suite's own per-test timeout still ends it.
