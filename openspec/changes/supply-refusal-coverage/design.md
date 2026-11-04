# Design

## Context

See [proposal.md](proposal.md). The coverage floor is a repository policy, and the project restores
it with dense tests of real refusal paths, not by changing the policy.

## Goals / Non-Goals

Goals: exercise every refusal path that the two supply Changes and the memo hardening added.

Non-goals: changing behavior, or lowering the floor.

## Decisions

- Parametrize one test over the malformed `mise ls` answers and one over the refusal remedies, so
  the cases stay in the existing modules.

## Risks / Trade-offs

None beyond test run time, which is under a second.
