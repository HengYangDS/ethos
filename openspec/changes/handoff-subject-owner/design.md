# Design

## Context

See the [proposal](proposal.md). The decision-density gate measures each function with complexipy
and refuses one that grows past its pin in `tests/fixtures/decision-density-baseline.json`; pins
only shrink.

## Goals / Non-Goals

Goals: one owner of the handoff subject rule, and every function at or below its pin.

Non-Goals: raising a pin.

## Decisions

1. `_package_subject(branch, package)` holds the rule; `_finish_report` stays unchanged, since
   export binds a required branch and needs no fallback.

## Risks / Trade-offs

None: a pure extraction of an expression both reports already evaluate.
