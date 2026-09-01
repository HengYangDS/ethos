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

### Change Relations And Learning

Change dependency inquiry and experimental learning are product capabilities;
they do not require permanent relationship or experiment entities. An edge in a
Change DAG exists only when the current official Change names a prior result as
an admission prerequisite and the current `TransitionPlan` binds its exact Git
object or Attestation. Git ancestry and the official OpenSpec archive provide
history. A resolver may project predecessors, successors, ready work, and blocked
work from those facts, but it never stores that projection as another graph.

A hypothesis, falsifier, or experiment procedure belongs in official OpenSpec
design and tasks. Its execution occurs in an owned Work Lane selected for the
exploration when isolation is useful. Observations and conclusions become
Attestations only when they must survive the execution. A later Change adopts a
result by naming it as current intent and binding its evidence; neither
`Commitment` nor `Lease` gains hypothesis, experiment, predecessor, or successor
fields.

### OpenSpec Acceptance And Closeout

A valid official Change always compiles a deterministic acceptance value. A
Change with requirement deltas compiles those requirements and scenarios; a
valid `skip_specs: true` Change compiles its acceptance from official metadata,
proposal, design, and tasks without inventing a no-op requirement. Authoring
readers distinguish an uncommitted or unavailable working-tree projection from
an unadopted repository. Executed proof binds an exact committed Git tree unless
an operation explicitly defines a different immutable input.

Archive moves official artifacts; it does not erase proof identity. Before or as
part of archive, ETHOS binds the compiled Commitment, source commit and tree,
selected artifact identity, and archive effect. Subsequent closeout selects the
applicable proof Attestation by predicate and exact bindings, not by scanning the
current archive as a database and not by substituting a transport, worktree, or
Git-effect receipt. Reopening or superseding intent creates a fresh official
Change; it does not mutate historical acceptance.

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

### Lane, Review, And Integration Roles

`work/*` is the authoring role. The candidate ref and checkout are local
integration resources. `proposal/*` is an unprotected review projection of an
already selected Git object; it is not a second authoring lane. In the ETHOS
repository, only `dev` and `main` are protected: `dev` is accepted integration
and `main` is release. An adopter may map different physical ref names while
preserving these semantic roles and protection boundaries.

A developer who cannot update protected `dev` directly publishes the selected
proposal object and uses the forge's MR or PR review path. A maintainer may apply
the same reviewed object through an exact compare-and-swap transition. Proposal
retirement depends on that object being accepted into `dev` and the review ref
being closed; it does not wait for a later, independent `dev` to `main` release
promotion.

Lease loss does not erase Git content and does not require historical Lease
resurrection. One public reconciler classifies owned, foreign, expired,
dead-owner, missing, and unbound lanes from fresh facts and yields one positive
transition: continue, hand off, reacquire, preserve, absorb, or retire. A clean
lane whose HEAD is equal to or already an ancestor of accepted truth may be
retired by deletion-only exact CAS after confirming the selected ref, clean
worktree or absent registered worktree, no live owner, and no unpublished unique
object. Dirty or ambiguous content remains preserved and observe-only.

A zero-product-change history reconciliation is a Git DAG operation, not a new
semantic state. It may create a signed descendant whose tree and compiled
Commitment are unchanged and whose additional parent is an explicitly observed
accepted peer head. Admission binds the exact parents, tree, signature, actor,
and ref CAS; no merge-specific compatibility carrier is created.

### Local Object Authority And Remote Projection

The local Git object database is the publication source of truth. A repository
with zero, one, or many declared remotes is valid. Each remote is an independent
projection target and receives the same selected commit and annotated-tag
objects by OID. A peer never becomes the source for another peer, and publication
never rebuilds, amends, re-signs, or replays content to satisfy a provider.

A multi-peer publication is one bounded plan with deterministic ordering and an
exact receipt. If a peer observes another peer before the same batch reaches it,
the result is a bounded `temporal_peer_projection_pending`, not proven
divergence; after the declared window, unequal OIDs are genuine divergence. A
local-only result claims neither remote publication nor hosted CI.

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

Proof selection is predicate- and binding-specific. A proof request selects the
Attestation for the exact Commitment, source commit and tree, gate policy,
verifier, and proof plane. An Attestation for worktree projection, transport,
ref movement, or another Commitment cannot satisfy that query merely because it
is newer or mentions the same path.

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

Continuation coordinates are typed by route: an execution session, execution
cell, and thread operation are not interchangeable. A long mutation writes its
deterministic receipt before the effect and reports whether the child process is
still live, whether mutation occurred, and the sole safe continuation. An
unsupported capability, wrong continuation route, and provider finalization
failure remain distinct; an observation failure never invites replay of a
possibly completed mutation. CLI examples use named arguments wherever a
positional value could be parsed as an option.

Repository-declared commands execute inside the repository's selected locked
toolchain, not ambient `PATH`. Failure evidence preserves the resolved binary,
argv, cwd, redacted effective path, actor, exit status, stdout, stderr, and
receipt path. Automated operation never opens an interactive password or
credential prompt; unavailable non-interactive authority blocks before effect
and returns one actionable command.

### Runtime And State Authority

Product version, distribution version, source commit, source tree, package or
wheel digest, runtime digest, accepted/candidate role, and installed runtime
binding are separate identities. A released version is never reused for
different bytes. Public version and status output expose these coordinates and
the embedded OpenSpec version.

Runtime activation is one transaction: preflight the complete offline closure
and state-schema compatibility; stage a public, versioned migration or safe
reset; construct and verify a new immutable generation; atomically switch
`CURRENT`; rebind and verify hooks; then reclaim superseded generations only
when no reference remains. Any failure restores selector, hooks, state, and
generation ownership to their exact pre-state. Immutable generations are never
modified in place, and cleanup restores owner permissions only within the exact
owned generation before deletion.

### Bounded Maintainer Recovery

Normal governance must remain escapable when the governor itself is inconsistent.
A maintainer break-glass transition is admitted only with an exact object, path,
or ref scope; current preconditions; explicit reason; non-interactive authority;
deterministic receipt; and mandatory post-effect observation and re-entry. It
cannot become a permanent hook bypass, wildcard permission, or substitute for
repairing the product owner.

Materiality is positive and semantic. Architecture, policy, behavior, and
durable user contracts require an official Change. A factual correction to a
projection may use a lean maintainer path only when fresh comparison proves that
it changes no product semantics, acceptance, or executable policy; that path is
still exact, reviewed, auditable, and Attested.

### Documentation, Evidence, And Operational Resources

Documentation is organized by reader purpose and semantic owner. In ETHOS,
`docs/README.md` is the sole documentation entrypoint and
`docs/guides/quickstart.md` is the first-run guide; a duplicate `docs/index.md`
has no role. A directory receives a README only when that file is the real
boundary or navigation owner for multiple meaningful children. Empty marker
directories and one-document directories with placeholder READMEs are removed.

`docs/decisions/` preserves only irreducible cross-Change rationale that the
current contract or source cannot express without losing alternatives,
consequences, or a revisit condition. Decision filenames are lowercase and
semantic, not numbered `DR-*` identities. A decision names its owner and
retirement condition. Top-level `evidence/` retains only immutable bytes with a
current producer, consumer, binding, and retention lifecycle; everything else
is absorbed into its owner or deleted.

Physical source layout follows [Module Layout Rules](../../rules/module_layout.md)
rather than being restated here. Quality likewise has one executable owner per
property: docstring coverage and style must be explicit, but a separate gate is
admitted only when it proves a property Ruff does not already own. Configuration
follows native tool resolution and one truthful evaluation root; another
repository's directory shape is not a reason to copy it.

Every temporary, runtime, supply, test, and generated tree has one owner and a
bounded lease or equivalent liveness fact. Normal completion uses structured
finalization; kill or crash is recovered by a bounded scavenger that protects
live owners and deletes only exact owned roots. Tests share read-only,
content-addressed dependency and runtime supply instead of copying complete
virtual environments or `node_modules` per case. Owned directory modes remain
deletable, and cleanup acceptance budgets item count, inode count, latency, and
host indexing pressure as well as bytes. Global monkeypatches, broad prefix
deletion, generic retries, and longer TTLs are not cleanup correctness.

### Evidence Planes And Completion Claims

Author identity, Git object signature, transport authentication, forge-side
verification, hosted CI, release assets, local proof, and installed runtime
readback are independent evidence planes. Generated commits must use a subject
admitted by repository policy. A claim names exactly which planes were freshly
verified; success in one never implies another.

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
6. OpenSpec is the sole tracked Change intent; Commitment is transient and
   Attestation is the durable semantic result.
7. Change relations and experiments remain derived capabilities, not new state
   stores.
8. Lease owns only lane-holder coordination; Git and proof facts are observed
   anew.
9. Local Git owns publication objects; every declared remote receives the same
   selected OIDs or is reported separately as absent, unavailable, pending, or
   divergent.
10. `work/*`, candidate, `proposal/*`, `dev`, and `main` have distinct authoring,
    integration, review, accepted, and release roles; proposal retirement follows
    `dev` acceptance, not `main` promotion.
11. Runtime activation, state migration, hook rebinding, and rollback form one
    immutable transaction executed through the locked repository toolchain.
12. Documentation, evidence, configuration, temporary resources, and physical
    modules survive only with one semantic owner, current consumers, and a
    provable lifecycle.
