---
subject: ethos:declarative-governance-compiler
role: explanation
state: canonical
relations:
  canonical_for: declarative governance compiler architecture
  decided_by: docs/decisions/DR-0005-declarative-lifecycle-spine.md
---

# Declarative Governance Compiler

Status: canonical.

Purpose: explain the declaration-first, functional center that compiles an
intended repository change into a deterministic, evidence-bearing transition.

See also: [DR-0005](../decisions/DR-0005-declarative-lifecycle-spine.md),
[TransitionPlan](transition-plan.md), and
[Terminal Governance Product Design](../plans/terminal-governance-product-design.md).

## Boundary

ETHOS is a compiler over repository truth, not a workflow engine or private
state authority:

```text
Commitment + Facts
              -> TransitionPlan
              -> verdict
              -> admitted effects
              -> Attestation
```

Git, filesystems, subprocesses, clocks, networks, and provider APIs remain at
explicit adapter boundaries. Contracts, policy decisions, plan compilation,
and reducers are deterministic transformations over supplied values.

## Spine

| Concern | Sole mechanism | Output |
| --- | --- | --- |
| Persisted contracts | strict frozen Pydantic v2 models | validated values and checked JSON Schema |
| Transient values | tuples, mappings, enums, and small frozen stdlib values | immutable facts and decisions |
| Predicates | typed facts plus CEL where plain declarations are insufficient | explained `pass`, `block`, or `unknown` verdicts |
| Dependency order | `TransitionPlan` and direct `graphlib.TopologicalSorter` | deterministic `Check`, `Decision`, and `Effect` order |
| CLI | Cyclopts declarations at the composition root | one human and machine command surface |
| Projections | pure reducers and native serializers | bounded status, protocol, and external carrier views |

Schemas may generate language bindings and externally required projections when
the schema is the sole owner and drift is checked. Generated output never
becomes a parallel hand-edited truth source.

## Functional Contract

```text
observe(root) -> Facts
compile(Commitment, Facts) -> TransitionPlan
judge(TransitionPlan, attestations) -> verdict
execute(admitted Effect) -> Attestation
```

Core transformations do not read files, spawn processes, inspect ambient Git
state, consult the clock, print output, or mutate hidden state. An adapter may
perform those effects only after receiving an explicit root, authority,
precondition, and permission boundary.

## Declaration Rule

A declaration must identify its authority, inputs, output contract, and proof
surface. Python is reserved for composition, I/O, mutation, and an algorithmic
primitive that cannot be expressed safely by the selected declaration or
standard-library mechanism.

No wrapper, registry, graph layer, event bus, DI container, or state-machine
framework is admitted merely to rename a mature owner. A new layer must carry a
distinct semantic obligation and prove a net reduction in total maintenance.
