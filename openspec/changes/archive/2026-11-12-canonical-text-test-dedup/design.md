# Design

## Context

See the [proposal](proposal.md). `test_no_behavior_is_implemented_twice` compares function bodies
after it renames the names each function binds, so a renamed copy is still a copy. The shared test
support owns the CLI runners.

## Goals / Non-Goals

Goals:

- The parallel-implementations test passes, and the canonical-text test proves what it proved.

Non-Goals:

- Moving `_command` out of `tests/unit/adapters/gates/test_source_format.py`, whose copy is now the
  only one.

## Decisions

1. The canonical-text test calls `run_ethos("lane", "format", ..., full_payload=False)` for the
   apply and the check. A non-zero exit fails the test through the helper's assertion, as the
   removed comparison of the exit code did.

## Risks / Trade-offs

- None: the helper and the removed copy run the same command and parse the same payload.
