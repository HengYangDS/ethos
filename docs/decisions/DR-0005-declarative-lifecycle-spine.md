---
subject: ethos:decision:declarative-lifecycle-spine
role: decision
state: canonical
relations:
  canonical_for: declarative lifecycle spine
  informs:
    - docs/architecture/declarative-governance-compiler.md
    - docs/architecture/transition-plan.md
    - docs/plans/terminal-governance-product-design.md
---

# DR-0005: Declarative Lifecycle Spine

Status: accepted.

Purpose: establish the singular declaration-first lifecycle spine for ETHOS
without ceding repository truth or lifecycle authority to a framework.

See also: [Decision Records](../README.md), [Decision Index](../decision-index.md),
[Declarative Governance Compiler](../../architecture/declarative-governance-compiler.md),
[TransitionPlan](../../architecture/transition-plan.md), and
[Terminal Governance Product Design](../../plans/terminal-governance-product-design.md).

## Record

| Field | Value |
| --- | --- |
| Decision ID | DR-0005 |
| Kind | architecture |
| Decision Makers | ETHOS maintainer and authorized work lane |
| Status | accepted |
| Decision Date | 2026-07-10 |
| Decision Version | 3 |
| Decision Change Date | 2026-07-26 |
| Record Review Date | 2026-10-10 |
| Supersedes | DR-0005 version 1 graph-wrapper and parallel-registry choices |
| Superseded By | None |
| Scope | Contract models, policy evaluation, TransitionPlan, CLI composition, serialization, projections, and anti-regression gates. |
| Boundary | ETHOS owns repository truth and transition semantics; frameworks and tools provide replaceable mechanisms only. |
| Decision | Use strict frozen Pydantic v2 models for persisted and external contracts, small frozen stdlib values internally, CEL for typed guard expressions after parity, direct `graphlib.TopologicalSorter` for TransitionPlan order, Cyclopts declarations as CLI truth, and checked JSON Schema for language-neutral contracts. |
| Consequences | Public contracts, rules, commands, projections, and plans are declaration-first. Python remains for pure compilation or explicit I/O and mutation adapters. Parallel registries, graph wrappers, compatibility layers, DI containers, and in-process event buses are not admitted without unique semantics and measured net benefit. |
| Proof or Evidence | The `terminal-convergence` OpenSpec change owns implementation and deletion proof; focused contract, determinism, schema, command, and HEAD-bound proof must pass before closeout. |
| Revisit Trigger | Revisit when declarations increase total maintenance, obscure authority, prevent explanation, or require an execution substrate to own lifecycle truth. |

## Rationale

ETHOS had accumulated procedural gap collection, dictionary normalization,
hand-written command glue, repeated dependency walkers, and generated surfaces
with overlapping ownership. The corrective principle is not “replace Python
with frameworks.” It is one semantic obligation, one owner, and the smallest
mature mechanism that preserves meaning.

The lifecycle spine is therefore:

1. **Contracts:** Pydantic v2 only at persisted or external boundaries.
2. **Facts:** freshly observed and passed explicitly; no ambient mutable truth.
3. **Rules:** declarations first, CEL only for predicates that need an expression
   language, and one selected CEL implementation after parity.
4. **Plans:** `TransitionPlan` contains `Check`, `Decision`, and `Effect` nodes; Python
   `graphlib` directly supplies cycle detection and topological order.
5. **Commands:** Cyclopts declarations own the command surface; documentation,
   schemas, and protocol metadata are derived rather than separately registered.
6. **Effects:** adapters execute admitted operations with explicit roots,
   permissions, expected state, and compare-and-swap preconditions.
7. **Evidence:** execution returns immutable attestations instead of publishing
   hidden events or mutating a second truth store.

Execution runtimes, workflow engines, policy servers, graph frameworks,
state-machine frameworks, DI containers, and event buses remain outside the
kernel. They may become optional adapters only after a real consumer proves
that the existing contracts and adapter protocol cannot express the requirement
more simply.

## Proof

Completion requires:

- contract and JSON Schema conformance;
- deterministic TransitionPlan digest, ordering, cycle, and replay properties;
- CEL parity before deleting the incumbent predicate path;
- one Cyclopts-owned command surface with projection drift checks;
- zero production graph wrappers or parallel command registries;
- terminal source budgets and a HEAD-bound complete proof.

## Invariants

- Repository truth and transition authority remain in ETHOS contracts.
- Every semantic obligation has one owner.
- Persisted models, CLI, predicates, DAG ordering, effects, and schemas each have one mechanism.
- A framework is admitted only for irreducible semantics and measured net benefit.

## Alternatives Considered

### Strict boundary models plus direct mature mechanisms

**Pros**

- Uses Pydantic v2, CEL, `graphlib`, Cyclopts, and JSON Schema without wrapping them in parallel owners.

**Cons**

- Requires strict parity, drift, determinism, and deletion proof.

**Why Rejected**

Not rejected; selected below.

### attrs, dataclass, and Pydantic dual models

**Pros**

- Reduces local migration friction.

**Cons**

- Creates conversion code, duplicate contracts, and duplicated tests.

**Why Rejected**

It violates singular persisted-contract ownership.

### Custom graph layer or a rich graph framework in the kernel

**Pros**

- Offers broader graph analytics.

**Cons**

- TransitionPlan needs only ordering and cycle detection; a wrapper becomes a second owner.

**Why Rejected**

Direct `graphlib.TopologicalSorter` is sufficient for kernel semantics.

### DI container, event bus, or workflow runtime as the product center

**Pros**

- Provides generic composition and orchestration abstractions.

**Cons**

- Obscures dependencies and risks creating another lifecycle truth plane.

**Why Rejected**

Explicit arguments, TransitionPlan, and Attestations already carry the required meaning.

## Selected Approach And Rationale

Use one mature mechanism directly for each irreducible concern and keep the
implementation centered on pure compilation plus explicit effects.

## Consequences

The selected stack is destructive: dual models, graph wrappers, command
registries, service locators, and event buses must be deleted rather than kept
as compatibility layers.

## Proof Or Evidence

- Contract/schema conformance.
- CEL parity, TransitionPlan determinism/cycle tests, and Cyclopts surface tests.
- Terminal source-budget and exact-HEAD proof.

## Revisit Trigger

Reopen when a real consumer proves the selected mechanisms cannot express an
irreducible requirement without semantic loss.

## Decision Change Ledger

| Version | Date | Change | Reason | Evidence |
| --- | --- | --- | --- | --- |
| 3 | 2026-07-26 | Selected the declaration-first terminal stack | Remove procedural and framework duplication | Terminal design and focused gates |
| 4 | 2026-07-28 | Added explicit alternatives and deletion consequences | Prevent reintroduction of parallel mechanisms | Terminal-convergence decision discipline |
