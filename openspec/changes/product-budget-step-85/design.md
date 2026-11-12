# Design

## Context

See the [proposal](proposal.md) and
[DR-0025](../../../docs/decisions/dr-0025-product-budget-step-85.md).

## Goals / Non-Goals

Goals:

- One reviewed step with the removal evidence that DR-0010 requires.

Non-Goals:

- Compressing or relabeling code, which the product design contract rejects as a repair.
- The structural reductions that DR-0020 assigned to 0.3.0.

## Decisions

1. The removal search covered the whole product: every top-level definition that no tracked file
   names again, and every function whose body is structurally identical to another. It found one
   dead definition and three identical groups, all three intended: typed SDK facades, the typing
   overloads of `run_git`, and two named path selectors.
2. The step is one 5,000 step, from 80,000 to 85,000.

## Risks / Trade-offs

- The ceiling stops forcing removal for the next 4,870 line-equivalents; DR-0025 names the revisit
  point.
