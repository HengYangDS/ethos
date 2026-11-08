# Design

## Context

See the [proposal](proposal.md). `tests/architecture/test_hang_bound.py` reads each
`pytest.mark.timeout` as a literal and refuses one at or above the shared bound.

## Goals / Non-Goals

Goals:

- A tight mark times only the operation it bounds, never its setup.
- One owner, the hang bound test, holds every rule about per-test marks.

Non-Goals:

- Timeouts that a test passes to the code under test on purpose.

## Decisions

1. A mark below the tool deadline, `seconds("tool")`, carries `func_only=True`; the hang bound test
   refuses one that does not. Marks stay literals, as that test requires.
2. The two native-run marks become 60, the tool deadline's value, since a native child's start on a
   loaded host is part of what they time.

## Risks / Trade-offs

- A real hang in the two native-run tests ends after 60 seconds instead of 5 or 30.
