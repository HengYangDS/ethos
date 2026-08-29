---
subject: ethos:product-design-contract
role: policy
state: canonical
relations:
  canonical_for: product meaning, semantic kernel, and carrier authority
---

# Product Design Contract

Status: canonical.

Purpose: own ETHOS product meaning, semantic roots, authority boundaries, and
the invariants every implementation and projection must preserve.

See also: [Kernel Model](../concepts/kernel-model.md), [Terminal Governance Product Design](../plans/terminal-governance-product-design.md), and [Command Plane](../reference/command-plane.md).

## Product

ETHOS is a proof-carrying compiler and transaction protocol for repository
change. It compiles an explicit commitment and fresh observations into a bounded
transition, rechecks its preconditions at effect time, and emits attestations of
what was observed, decided, and effected.

Its product promise is not “more governance.” It is the shortest trustworthy
path from change intent to repository effect: preserve intent, expose the one
current blocker or next action, reuse native repository capabilities, and make
every completed claim independently verifiable and recoverable after an agent,
session, host, or forge is lost.

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

The semantic values are:

| Root | Owns | Excludes |
| --- | --- | --- |
| `Commitment` | transient normalized acceptance intent with exactly `schema_version`, `id`, and `acceptance`, compiled from one exact official OpenSpec Change snapshot | persistence, a second tracked intent carrier, authoring scope, dependency graph, mutable workflow state, or reusable permission |
| `Attestation` | verifier-bound observation, judgment, proof, or effect with predicate, bindings, validity, and evidence | an implicit authority or closed predicate taxonomy |

Only `Attestation` is a durable semantic result. `Commitment`, `Facts`, and
`TransitionPlan` are transient values bound to exact inputs.

Semantic validity belongs to typed meaning, not carrier presentation. The kernel
validates members, duplicates, references, and conflicts, then normalizes
unordered collections before identity. Exact canonical-byte checks remain
confined to readers for already content-addressed envelopes.

`Commitment` is a compiled value, not an ETHOS-authored file. Mutation-capable
repositories use the official OpenSpec Change artifacts as the sole tracked
intent, specification, design, task-progress, and archive carrier. ETHOS
normalizes the exact official projection selected from one Git tree into a
Commitment for planning and proof; it never asks an author to repeat that
meaning in another tracked schema.

The compiled Commitment contains only semantics that affect acceptance. It does
not own anticipated paths, relation records, research DSLs, authority
references, risks, or progress. Exact changed paths and Git
coordinates are fresh `Facts` bound by a `TransitionPlan`. A dependency is an
explicit plan input only when its satisfaction changes current admission;
related Changes are query projections, not persisted fields. Research questions
and procedures remain native OpenSpec design/spec/task content, while
observations and conclusions are Attestations.

```text
(Commitment, Facts, prior Attestations) -> TransitionPlan -> new Attestations
```

The common mechanism is:

```text
observe -> extract -> resolve -> compile -> evaluate -> CAS apply -> post-observe -> attest -> project
```

`project` may render CLI, SDK, CI, forge, documentation, or agent views. A
projection never grants itself authority.

`Continuation` is a pure, non-persistent projection from the schema-version-`2`
result and current authoritative facts. The result preserves `state` and
`required_gaps`, exposes singular `next_action` and `user_decision_required`,
and derives `continuation` as exactly one of `continue`, `await-user`,
`blocked`, or `done`. `missing_facts_or_evidence` derives from `required_gaps`
only for an `unknown` verdict. Continuation never becomes a second lifecycle
state.

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
release_root -> accepted_root -> candidate -> work_lane; proved candidate objects may be projected to proposal_ref
```

This topology names Git resource roles, not semantic entities. Dirty, foreign,
unknown, unbound, or stale resource state is observe-only until fresh facts and
bindings admit a transition.

A Lease is only the expiring compare-and-swap relationship between one lane and
its current holder. Its authoritative state is the lane identity, holder,
generation, and expiry. It does not persist HEAD, tree, index, worktree,
OpenSpec identity, Commitment, path scope, handoff workflow, or effect outcome.
Those belong to fresh Facts, transient compilation, exact effect intent,
Attestations, and post-observation.

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

Proof admission binds the compiled Commitment identity and exact repository
Facts before mutable dependencies or conflicts are evaluated. Historical
Attestations remain queryable, but proof for another input cannot invalidate
candidate acceptance. Conflicts within the selected authority remain
fail-closed.

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

The semantic kernel remains independent of OpenSpec types. Complete,
mutation-capable adoption nevertheless pins verified OpenSpec as the sole
Change, design, spec, task-progress, dependency, and archive carrier. The
official CLI owns those semantics. A repository may omit OpenSpec only while it
remains observation-only; material governed mutation then fails closed.

Before ETHOS introduces any carrier, schema, persisted record, command-local
receipt, lifecycle state, or semantic type, the design must answer all three
questions affirmatively:

1. Is the obligation absent from official OpenSpec, Git, Commitment,
   TransitionPlan, Attestation, and the existing effect adapters?
2. Would deleting the proposed entity make a required invariant mechanically
   unprovable rather than merely less convenient?
3. Does the entity have one bounded owner and an explicit terminal deletion or
   retention condition?

Failure of any question means the entity is not admitted.

### First-Hour UX

The first hour is a bounded reader followed by the same lifecycle:

```text
status -> plan -> prove -> land -> publish
```

`status` exposes facts, authority, gaps, coordination signals, and the next
admissible action without minting truth. `adopt` binds an external repository to
that lifecycle through an explicit, reviewable plan, initializes and verifies
OpenSpec for mutation-capable use, and does not create a parallel lifecycle.
Hidden lane and hook operations support admission only.

The public product surface is deliberately small and capability-complete:

| Surface | Role |
| --- | --- |
| CLI | Human-readable progressive disclosure and stable machine JSON over the same result. |
| Python SDK | Typed in-process access to kernel compilation, observation, evaluation, and projection without shell parsing. |
| Schemas and conformance kit | Language-neutral contracts, fixtures, and expected verdicts for independent clients. |
| MCP or A2A adapter | Optional stateless protocol projection over the SDK; it owns no task, lifecycle, session, or repository truth. |
| CI and forge projections | Native provider syntax that invokes the same declared proof capabilities and preserves proof-plane identity. |

UX and DX are kernel properties, not documentation polish. A normal path asks
only for facts that change the next action; advanced detail is available without
hiding a gap. Every block names what happened, why it blocks, its evidence or
missing fact, the one safe next action, and whether a human decision is required.
Human and JSON views preserve the same verdict and semantic identifiers. Local
operation is deterministic and offline after bootstrap; commands bind the current
worktree, project `.venv`, lock, and source, never a global installation. Adoption
is previewable, idempotent, minimally invasive, reversible before first governed
effect, and cleanly uninstallable without leaving hooks, generated truth, or a
second control plane.

## Feedback Intent Preservation

Every accepted feedback item has one of two durable outcomes: it is mapped to a
named semantic owner with acceptance and proof, or it records an explicit
absence reason. A refinement may change a carrier only after its invariant,
owner, acceptance, and verifier remain traceable. This preserves intent while
allowing deletion of redundant prose and mechanisms.

## Bounded Change Granularity

One official OpenSpec Change owns one bounded intent and its task progress. It is
too large when its open obligations cannot be ordered, reviewed, proved, and
closed as one coherent outcome. Split only when each resulting Change can land a
useful semantic outcome without duplicating authority or progress. Moving an
obligation never counts as implementing it.

New intent does not expand an active Change merely because it arrives before
closeout. Create another official Change after the current atomic boundary, or
record a non-authorizing Attestation when only evidence must survive. ETHOS does
not persist relationship fields merely to narrate history: Git and official
archive facts already provide sequence, and related Changes are query projections.
When a specific prior result is a genuine admission prerequisite, the current
TransitionPlan selects its exact Attestation and fails closed if it is absent.

Concurrency is decided from fresh lane ownership, exact candidate effects, and
current conflicts rather than predicted path globs. Capacity, risk, overlap, and
proof cost may inform the decision, but no queue, mutable program state,
parallel task list, dependency ledger, or lifecycle database selects current
work. Integration remains a short exact-CAS boundary.

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
5. Profiles retain native domain, layout, provider, and observation freedom;
   complete mutation adoption uses one verified OpenSpec carrier without
   shaping kernel semantics.
