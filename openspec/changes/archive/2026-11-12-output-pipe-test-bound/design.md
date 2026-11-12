# Design

## Context

See the [proposal](proposal.md). A fixed wall-clock bound on a subprocess that starts Python fails
when the host is busy; the shared tool deadline is the bound that test support already uses
(`tests/support/subprocesses.py:37`).

## Goals / Non-Goals

Goals:

- The test stops failing on host load while still failing on a hang.

Non-Goals:

- Changing the output module or any other bound.

## Decisions

1. `process.communicate(timeout=seconds("tool"))`, with `seconds` imported from
   `ethos.repository.paradigm.parameters`.

## Risks / Trade-offs

- A hang now takes the tool deadline to surface instead of 5 seconds; the proof's own gate deadline
  still bounds the run.
