---
subject: ethos:product-design-contract
role: policy
state: canonical
relations:
  canonical_for: product meaning, semantic kernel, and carrier authority
---

# Product Design Contract

## Product

ETHOS is a proof-carrying compiler and transaction protocol for repository
change. It compiles an explicit commitment and fresh observations into a bounded
transition, rechecks its preconditions at effect time, and emits attestations of
what was observed, decided, and effected.

ETHOS is local-first and vendor-neutral. Git, forges, CI, OpenSpec, agent
runtimes, and task systems remain native systems or adapters; none becomes an
ETHOS-owned truth store merely by being connected to it. Local, GitLab, and
GitHub observations are distinct proof planes.

## Root Constraint

> 道隐无名，几动于微，法乎自然；
> 生一启元，分二判势，孕三冲和；
> 万象昭幽，度协畛域，枢得环中；
> 物遂其性，化育无穷，是谓玄德。

This constrains judgment: preserve meaning with the smallest model, distinguish
only what changes action, keep authority separate from views, and retire a
mechanism when its obligation disappears. [Engineering Axioms](../../system/axioms.md)
derive checkable constraints from this section; they do not own product meaning.

## Semantic Kernel

The only durable semantic roots are:

| Root | Owns | Excludes |
| --- | --- | --- |
| `Commitment` | immutable intent, subject, scope, invariants, acceptance propositions, and authority reference | mutable workflow state or reusable permission |
| `Attestation` | verifier-bound observation, judgment, proof, or effect with predicate, bindings, validity, and evidence | an implicit authority or closed predicate taxonomy |

`Facts` are fresh, context-bound observations. `TransitionPlan` is deterministic,
transient IR bound to exact inputs. Neither is a durable semantic root.

```text
(Commitment, Facts, prior Attestations) -> TransitionPlan -> new Attestations
```

The common mechanism is:

```text
observe -> extract -> resolve -> compile -> evaluate -> CAS apply -> post-observe -> attest -> project
```

`project` may render CLI, SDK, CI, forge, documentation, or agent views. A
projection never grants itself authority.

### Model Promotion

A `contradiction` or `model_gap` means that valid input cannot be reconciled or
represented losslessly. It must block effects and retirement. Preserve the
conflicting scenarios and evidence, promote the smallest affected model
boundary, recompile dependent plans and projections, verify coverage, then
absorb or retire the residue. Do not add an exception, alias, fallback, shim,
or parallel truth. `model_promotion_required` is the explicit blocking outcome
while that work remains open.

## Invalid-State Taxonomy

The invalid-state taxonomy is open, not a closed ontology. Operations may
preserve an unknown signal, but only predicates understood by the selected
operation may authorize an effect. At minimum, these blocking classes remain
machine-distinguishable:

```text
unknown_required_fact
ambiguous_authority
stale_binding
contradiction
model_gap
model_promotion_required
```

A new class is admitted by Model Promotion when it preserves a distinction that
changes evaluation or recovery; it is not introduced merely to label history.

## Git-Native Repository Substrate

ETHOS is Git-native, not a generic VCS abstraction. Git trees, refs, exact
heads, and compare-and-swap ref updates are the repository substrate for an
effect. A profile may map the self-hosted integration topology as:

```text
release_root -> accepted_root -> candidate -> work_lane -> proposal_lane
```

This topology names Git resource roles, not semantic entities. Dirty, foreign,
unknown, unbound, or stale resource state is observe-only until fresh facts and
bindings admit a transition.

### Binding Taxonomy

A binding is explicit and exact in its authority query:

1. **Product-semantic hard bindings** bind kernel inputs, subject, scope,
   predicate, validity, and expected Git state.
2. **Mandatory governance dependencies** bind a profile-selected operational
   obligation whose absence blocks the operation.
3. **Profile or adapter bindings** bind optional native carriers and external
   capabilities; absence is a fact with an explicit reason, never a fabricated
   default.

Bindings do not transfer authority between proof planes. A fresh binding may
establish currentness only for its declared subject, predicate, scope, plane,
and validity boundary.

### Configuration Boundaries

Configuration has one owner per concern: repository source owns behavior,
`system/` owns machine declarations, `.config/checks/<concern>/` owns an
admitted check's local inputs, and native provider files own provider syntax.
`system/tools.toml` records tool admission rather than duplicating each tool's
configuration. This separation of concerns implements MECE, SSOT, and DRY; a
projection links to its owner instead of copying policy.

## Isomorphic Adopter Governance

ETHOS and an adopted repository use the same kernel and transaction protocol.
Profiles and adapters select native carriers, checks, and proof depth; they do
not create another command plane, ontology, or truth store. This is not product
cloning: each repository retains its domain model, layout, and provider shape.

OpenSpec is a selectable carrier for the ETHOS profile. Its official CLI owns
OpenSpec validation and archival mutation. An adopter without `openspec/` is a
valid profile outcome.

### First-Hour UX

The first hour is a bounded reader followed by the same lifecycle:

```text
status -> plan -> prove -> land -> publish
```

`status` exposes facts, authority, gaps, coordination signals, and the next
admissible action without minting truth. `adopt` binds an external repository to
that lifecycle through an explicit, reviewable plan; it does not create a
parallel lifecycle. Hidden lane and hook operations support admission only.

## Feedback Intent Preservation

Every accepted feedback item has one of two durable outcomes: it is mapped to a
named semantic owner with acceptance and proof, or it records an explicit
absence reason. A refinement may change a carrier only after its invariant,
owner, acceptance, and verifier remain traceable. This preserves intent while
allowing deletion of redundant prose and mechanisms.

## Projection Homomorphism

A projection is homomorphic only when it preserves the source assertion's
identity, subject, predicate, scope, plane, bindings, validity, provenance, and
absence reason. It may reduce presentation, but must not invent authority,
conceal a required gap, or reverse-own its source. External observations enter
the kernel as Facts or Attestations with their verifier and validity boundary;
their rendered dashboards, indexes, and command output remain projections.

## Invariants

1. One durable obligation has one narrow semantic owner.
2. Every effect is compiled, evaluated, current-state checked, and CAS applied.
3. Unknown required facts, ambiguous authority, stale bindings, and contradictions
   fail closed.
4. Historical bytes remain readable but do not silently authorize current work.
5. Profiles retain native-carrier freedom without changing kernel semantics.
