# Design

## Context

See the [proposal](proposal.md). DR-0020 took the product step the same way.

## Goals / Non-Goals

Goals: one reviewed 5,000 step for the tests, with its removals and consumers recorded.

Non-Goals: a product or tools step, compressing or relabeling tests, and the consumers' own work.

## Decisions

1. The removals counted are measured on the enforced token measure: the duplicated test behaviors
   (`test-parallel-implementations`, -139), Phase T step 1 (`fixture-signer-owner`, -13) and step 2
   (`repository-spec`, +0), and `catalog-groups` (-12, -227 effective lines).
2. The step is taken now, ahead of both consumers, so neither consumer's first test commit fails
   the gate and neither Change carries the budget decision.

## Risks / Trade-offs

The space is shared: a consumer that overruns its estimate takes from the other. DR-0023 names the
revisit point.
