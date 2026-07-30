---
subject: ethos:learning
role: explanation
state: canonical
relations:
  canonical_for: repository learning and program relations
---

# Learning And Program Relations

Status: canonical.

Purpose: explain how hypotheses, experiments, and multi-change relations remain
available without a parallel lifecycle database.

See also: [Product Design Contract](product-design-contract.md) and
[Command Plane](../reference/command-plane.md).

Hypotheses, experiment strategy, dependencies, and optional program relations
belong to immutable `Commitment` values. A changed hypothesis or strategy
creates a new Commitment. Observations, judgments, proofs, and effects belong to
content-addressed Attestations. Any program view is derived from
dependency-connected Commitments, current Facts, and bound Attestations.

There is no separate ledger, mutable program state, step/closeout database, CEL
plane, or command family for this purpose. Historical ledgers and records remain
immutable bytes and cannot participate in a current verdict.

`ethos status --json` projects current lifecycle gaps. `ethos prove --full
--json` evaluates the configured local proof plan. `ethos land --json` and
`ethos publish --json` consume their own current readiness facts.

A hypothesis or program relation is not proof by itself. An accepted result
remains bound to the effective Commitment, exact HEAD, TransitionPlan, evidence, and
Attestation verdict.
