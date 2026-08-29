---
subject: ethos:transition-plan
role: explanation
state: canonical
relations:
  canonical_for: transient transition planning
  derives_from: ../governance/product-design-contract.md#semantic-kernel
---

# Transition Plan

Status: canonical.

Purpose: define the one transient planning algebra without creating a durable
workflow or truth store.

See also: [Kernel Model](../concepts/kernel-model.md), [Declarative Governance Compiler](declarative-governance-compiler.md), and [Protocol Contracts](protocol-contracts.md).

A `TransitionPlan` is the transient, deterministic projection of one three-field
`Commitment`, freshly observed `Facts`, policy, and applicable `Attestations`.
It orders checks, decisions, and effects; it is neither persisted intent nor a
second workflow state.

```text
Commitment + Facts + Attestations
  -> resolve authority and contradictions
  -> compile checks, decisions, and effects
  -> topologically order nodes
  -> evaluate pass | block | unknown
  -> exact ref-intent CAS effects
  -> post-observe and attest
```

## Contract

- Inputs are explicit values; compilation does not read ambient files, clocks,
  networks, processes, or mutable state.
- Node identity, dependencies, inputs, and expected state determine a stable
  digest. Equivalent inputs produce byte-stable plans.
- Dependencies form a DAG ordered directly by
  `graphlib.TopologicalSorter`; cycles block compilation.
- `Check` observes or validates, `Decision` resolves whether execution is
  admitted, and `Effect` describes one idempotent compare-and-swap mutation.
- Missing required facts, unknown predicates, unresolved authority, and
  contradictions produce `unknown` or `block`; neither permits effects.
- Adapters execute only admitted effects with an explicit root, authority,
  precondition, and expected state, then return immutable `Attestation`s.

## Boundary

`TransitionPlan` is regenerated whenever its inputs change and is never the
owner of campaign progress, task state, Git history, repository facts, or
provider state. Command JSON and evidence may project the plan and its digest,
but no projection may become a parallel editable truth.
