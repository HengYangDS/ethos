---
subject: ethos:commitment-relations
role: explanation
state: projection
relations:
  projects:
    - docs/governance/product-design-contract.md#semantic-kernel
---

# Learning And Successor Commitment Relations

Status: explanatory projection.

Purpose: explain how hypotheses, experiments, and bounded successor relations
remain available without a parallel lifecycle authority.

See also: [Product Design Contract](product-design-contract.md) and
[Command Plane](../reference/command-plane.md).

Hypotheses, experiment strategy, and dependencies belong to immutable
`Commitment` values. A changed hypothesis, strategy, or bounded intent creates a
successor Commitment. Observations, judgments, proofs, and effects belong to
content-addressed Attestations. Any multi-change view is derived from
dependency-connected Commitments, current Facts, and selected Attestations.

There is no separate ledger, mutable program state, step/closeout database, CEL
plane, or command family for this purpose. Historical ledgers and records remain
immutable bytes and cannot participate in a current verdict.

Current progress comes only from the selected active Change's `tasks.md` under
its Commitment. Dependency views may order declared Commitments but cannot
select current work, mutate task state, or make archive bytes current.

`ethos status --json` projects current lifecycle gaps. `ethos prove --full
--json` evaluates the configured local proof plan. `ethos land --json` and
`ethos publish --json` consume their own current readiness facts.

A hypothesis or dependency relation is not proof by itself. An accepted result
remains bound to the effective Commitment, exact HEAD, TransitionPlan, evidence,
and Attestation verdict.
