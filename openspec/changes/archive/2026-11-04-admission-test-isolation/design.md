# Design

## Context

See [proposal.md](proposal.md). `tests/conftest.py` owns each test's process environment through
the autouse `_hermetic_process_environment` fixture. It already pins Git, the actor, the data homes
and `ETHOS_PROOF_HOST_LOAD_LIMIT`.

## Goals / Non-Goals

Goals:

- No test inherits the host admission of the proof that runs it.

Non-goals:

- Any change to how a proof admits itself or what it exports.

## Decisions

- Remove the variables in the existing fixture, the one owner of a test's environment, not in each
  test.
- Name them through the product's constants, so a renamed variable cannot leave a stale list.
- Keep `PYTEST_XDIST_AUTO_NUM_WORKERS`. xdist reads it when the run starts, before any test, and it
  caps only the worker count.

## Risks / Trade-offs

- A future admission variable needs adding here too. Reading it from the product's constants keeps
  that one edit next to the product's own declaration.
