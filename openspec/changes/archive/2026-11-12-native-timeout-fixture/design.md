# Design

## Context

See the [proposal](proposal.md). `native_attempt` in `src/ethos/adapters/gates/native/attempt.py`
keeps a timed-out command's partial stdout and reads every declared output that exists when the
command stops. It archives a report without checking which tool wrote it.

## Goals / Non-Goals

Goals:

- The timeout test's outcome does not depend on how fast the runner runs pytest, coverage or Ruff.
- The test keeps its 15-second budget and its assertions.

Non-Goals:

- Any change to how ETHOS runs native gates or handles their timeouts.
- A larger budget: the test always waits for the whole budget, so every run would pay for it.

## Decisions

1. With `OUTCOME == "timeout"`, the behavior session first writes a minimal JUnit document to
   `behavior.xml`, then runs the sentinel step (print, then sleep for 60 seconds). Pytest and the
   static session never start.
2. The static session's timeout step is removed.
3. Proof of the margin: with the budget cut below the old critical path for one run, the old
   fixture fails on the missing sentinel and the new one passes. That cut is not committed.

## Risks / Trade-offs

- The timeout test no longer runs pytest before the timeout. What it proves does not depend on
  which tool wrote the report: partial stdout and the reports present are retained, and the scratch
  directory is removed.
- Nox's startup alone could still use up 15 seconds on a runner loaded far beyond this one. The
  test would then fail the same way, and the budget is the next lever.
