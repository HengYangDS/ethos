---
subject: ethos:terminal-governance-product-design
role: plan
state: canonical
relations:
  canonical_for: terminal architecture and convergence route
  projects: ../governance/product-design-contract.md#model-promotion
---

# Terminal Governance Product Design

Status: canonical terminal plan.

Purpose: project the product contract into the shortest convergence order for
implementation, proof, deletion, adoption, and publication.

See also: [Product Design Contract](../governance/product-design-contract.md).

## Role

This plan owns terminal architecture and convergence order. The [Product Design
Contract](../governance/product-design-contract.md#semantic-kernel) remains the
sole owner of product meaning; this document specifies how implementations,
projections, and deletions converge on it.

## Architecture

### Semantic Authority And Projection Homomorphism

The implementation compiles the semantic kernel into transport and presentation
surfaces without changing assertion identity. Every projection preserves source
identity, provenance, bindings, validity, and an external observation's absence
reason; it cannot mint authority or hide a required gap. Isomorphism is checked
across the product repository and adopters by comparing the same kernel inputs,
verdict boundary, and attestation shape rather than their physical layouts.

The terminal architecture declaration under
`system/projections/terminal-architecture/` selects the complete visual
assertion set and its absence reasons. It is not a second product ontology: the
product contract remains semantic authority. The read-only exporter binds that
declaration and every selected source to one exact Git commit and tree, emits a
content-addressed `projection.input/v1`, and grants no repository-effect
authority. Renderers and diagram tools consume the export; they never write
back or become an authority root.

### Model Promotion

[Model Promotion](../governance/product-design-contract.md#model-promotion) is
the only response to a lossless-model failure. Its implementation boundary must
preserve the conflicting evidence, block effect and retirement, recompile
affected projections, and prove the replacement has one semantic owner.

### Git-Native Transaction Boundary

Effects bind freshly observed Git coordinates and one exact ref intent into a
`TransitionPlan`, recheck them, execute one compare-and-swap, then post-observe
and attest.
Worktrees, lanes, leases, and integration refs are resource coordination, not
semantic roots. Their transition may not substitute stale facts, a dashboard,
or a hosted result for the local Git binding.

### Repository Semantic Panorama

The repository is governed by semantic obligations, not by its current file
layout. The following table is the destructive-convergence map for active
implementation owners. A listed current surface is evidence of where an
obligation is implemented today, not a reason to retain that surface.

| Obligation | Current implementation owners | Terminal owner and disposition |
| --- | --- | --- |
| Intent and completed proof | official OpenSpec artifacts, Commitment compiler, Attestations, evidence adapters | Official OpenSpec is the sole tracked intent carrier. Commitment is a transient three-field compilation; Attestations durably own completed proof. |
| Observation, decision, and continuation | status, plan, prewrite, hook admission, result projection, command-local resolvers | One typed resolver compiles fresh `Facts` and selected authority into one result and continuation. CLI, hooks, SDK, and skills consume it; they do not reinterpret it. |
| Local Git ref mutation | common Git-effect executor plus archive, lane-start, retirement, landing, refresh, and attestation-set ref writers | One Git-ref effect adapter owns admission, exact CAS, post-observation, compensation, recovery evidence, and effect Attestation. Delete command-specific ref-effect state machines after migrating unique pre/postconditions. |
| Worktree and filesystem mutation | worktree helpers plus lane-start, retirement, handoff, hook, archive, and accepted-root orchestration | One worktree/filesystem effect adapter implements reversible primitives under the common transaction protocol. Lifecycle commands compile plans; they do not own rollback frameworks. |
| Lease and shared state mutation | SQLite Lease lifecycle plus command-specific finalization, archive, handoff, and retirement logic | One row stores only lane, holder, CAS generation, and expiry. Git, OpenSpec, Commitment, workflow, and effect state remain outside it; handoff uses exact facts, request evidence, and one holder CAS. |
| Remote publication | publication request receipts, forge adapters, proposal/promotion command paths | One remote-effect adapter preserves bounded exact-ref observations as present, absent, or unavailable; only observed OIDs enter admission or effect compilation. It models applied, unknown, and re-observed outcomes. GitHub, GitLab, and local-only are peer projections. `proposal/*` is a governed review ref projection, never an authoring lane. |
| Runtime, package, and hooks | build identity, runtime selector/materialization, hook binding/activation, package readback | One immutable BuildIdentity and one runtime transition adapter own installation, upgrade, self-heal, rollback, and readback. Package version is never reused for different bytes. |
| Recovery and compensation | Git-effect recovery plus archive, lane-start, retirement, handoff, publication, runtime, and config-specific recovery | Recovery re-observes an exact plan and effect class. An effect may retain evidence needed to resume or compensate, but no command owns a parallel lifecycle or generic mutable recovery state. |
| Assurance | gate compiler/runner, proof admission, OpenSpec task checks, hosted and independent verification adapters | Acceptance propositions compile to proof obligations and verifier-bound Attestations. Tasks express progress, paths name inputs, and neither substitutes for proof. Pre-publication and hosted evidence remain distinct phases. |
| Operational integrity | quality gates, source budgets, semantic closure, reference closure, package/runtime checks, temporary-resource owners | One executable quality graph owns each obligation once. Size thresholds are tripwires, not proof of redundancy; structural duplication, competing owners, unreachable symbols, and semantic overlap determine deletion. |

Fresh observations bound every current transition. In particular, explicit
changed-scope planning terminates as a successful no-op when Git reports no
changed paths; it does not recover historical OpenSpec intent, compile proof
work, or let an archive Attestation manufacture a current scope. Non-empty
archive transitions retain their exact scope and Attestation checks.

The five effect classes are `git-ref`, `worktree/filesystem`, `lease/state`,
`remote`, and `runtime/package`. They share one protocol:

```text
fresh observe
-> deterministic TransitionPlan
-> effect-time admission and exact binding recheck
-> effect-class apply
-> post-observe
-> Attestation
-> idempotent resume or bounded compensation
```

They do not share one oversized implementation function. Each adapter owns only
the irreducible native operation for its effect class; lifecycle commands own
neither mutation primitives nor recovery state machines.

Remote publication cannot derive history from a missing fact. An unavailable
preflight observation yields `unknown` before any push; an unavailable
post-write observation yields `outcome_unknown` without claiming that the peer
was updated. Observed divergence remains `block`. Peer ordering and bounded
temporal parity across declared forges remain part of the assurance and
publication batch rather than this observation boundary.

The dependency-ordered destructive batches are finite. A batch is not complete
because its target behavior appears in this document or because a focused test
passes; its own official Change must close the stated exit boundary.

1. **Close design authority.** Reconcile the product contract and this plan,
   validate their official OpenSpec Change, and remove any statement that makes
   archived tasks or recovered conversation text the current queue. Exit when
   the two documents are complete, non-duplicative, and make no implementation
   or hosted-state claim.
2. **Close OpenSpec compilation and the shared resolver.** Make every valid
   official Change, including `skip_specs: true`, compile deterministic
   acceptance without a duplicate carrier. Distinguish uncommitted projection,
   invalid Change, missing adoption, and archived intent; preserve proofability
   across archive; select proof Attestations by exact predicate and bindings;
   and derive Change relations and experiments without persistent graph or DSL
   state. Converge status, plan, prewrite, hooks, prove, archive, and closeout on
   one resolver and typed continuation. Exit when their verdict, root cause, and
   sole next action agree for active, uncommitted, archived, reopened, no-spec,
   and malformed Changes, and active runtime contains no tracked Commitment,
   rebind, predecessor, or successor authority.
3. **Close local effects and lane coordination.** Route Git refs,
   worktree/filesystem changes, and Lease/state changes through their one native
   effect owners. Reduce Lease to lane, holder, generation, and expiry. Provide
   positive public transitions for start, continue, handoff, reacquire, absorb,
   preserve, and exact-equal deletion-only retirement, including missing,
   expired, unbound, and dead-owner cases. Admit zero-tree-change Git DAG
   reconciliation by exact parents, tree, signature, actor, and CAS. Exit when
   interrupted effects resume or compensate without duplicate state machines,
   clean absorbed lanes retire without reconstructing historical Lease state,
   and dirty or ambiguous work remains untouched.
4. **Close runtime, state, command execution, and diagnostics.** Give product,
   distribution, source commit/tree, package digest, runtime digest, selected
   role, and installed binding distinct immutable identities. Make activation
   preflight the complete offline closure and state schema; migrate or safely
   reset through one public versioned operation; build a new immutable
   generation; atomically switch `CURRENT`, hooks, and state; verify; roll back
   exactly; and reclaim only unreferenced generations. Run repository gates once
   inside the declared locked toolchain. Exit when fresh and legacy adopters can
   self-heal without SQLite edits, ambient `PATH`, in-place runtime writes,
   password prompts, or residual refs/worktrees, and every failure preserves
   exact execution facts plus a typed non-replaying continuation.
5. **Close integration and publication topology.** Enforce `work/*` authoring,
   local candidate integration, unprotected `proposal/*` review, protected `dev`
   acceptance, and protected `main` release. Developer delivery uses MR/PR;
   maintainer delivery uses reviewed exact CAS or bounded break-glass. Retire a
   proposal after its selected object enters `dev` and its review ref closes,
   independently of later `main` promotion. Publish the same local commit and
   annotated-tag OIDs to zero, one, or many independent peers through one
   deterministic batch; classify bounded in-flight parity separately from true
   divergence. Exit when local-only, GitLab-only, GitHub-only, and dual-peer
   cases pass without replay, rebuild, re-signing, implicit primary remote, or
   cross-peer authority.
6. **Close semantic and physical repository structure.** Apply the existing
   module-layout rule repository-wide; remove empty shells, accidental
   one-module packages, suffix-flat splits, facades, and stale imports while
   retaining real namespaces. Reconcile documentation to one entrypoint,
   `guides/quickstart.md`, necessary READMEs, and a restored
   `docs/decisions/` containing only irreducible lowercase semantic records.
   Classify top-level evidence by real producer, consumer, binding, and
   retention; remove residue. Prove one quality owner per property, including
   docstrings and native configuration placement. Exit when semantic ownership
   reports no missing, duplicate, orphan, superseded-active, or conflicting
   relation and every generated projection matches its source.
7. **Close temporary-resource and supply ownership.** Give every temporary,
   runtime, test, and supply tree an owner and liveness lease; use structured
   finalization plus bounded dead-owner scavenging; protect live roots; and make
   exact owned trees deletable even when their contents are read-only. Replace
   per-test copies of full Python runtimes, virtual environments, and
   `node_modules` with shared read-only content-addressed supply and minimal
   fixtures. Exit after normal exit and kill/crash tests show bounded zero or
   policy-limited residue across `/private/tmp`, Darwin user temp roots, and uv
   cache, within declared item, inode, byte, deletion-latency, and indexing-load
   budgets.
8. **Close assurance and adopter conformance.** Compile requirement coverage
   into exact proof obligations and keep author identity, Git signature,
   transport authentication, forge verification, hosted CI, release assets,
   local proof, and installed runtime readback separate. Run product, greenfield,
   brownfield, docs/infra, package-only, local-only, single-peer, dual-peer,
   interrupted, drifted, unbound, and adversarial fixtures through the same
   kernel. Inspect AIGW and Proxy read-only only after the package runtime is
   accepted. Exit when every requested plane has fresh evidence and no adopter
   compatibility carrier or copied state machine is required.

Only disjoint read-only audits may overlap freely. Mutation that touches one
authority owner and its consumers is serial: one bounded official Change, one
owner, one accepted outcome, then cleanup before the next overlapping Change.
At the start of every batch, fresh facts may prove some work already satisfied;
that evidence closes the item without reimplementation. Reordering requires a
proved prerequisite, not convenience.

### Adopter Isomorphism And First-Hour UX

The product repository and adopters run the same kernel through profiles and
adapters, not product cloning. The first hour is deliberately small:

```text
status -> plan -> prove -> land -> publish
```

`status` is the read-only entrypoint. `adopt` proposes an explicit binding to
that loop; an absent optional carrier remains an observed profile fact.

### Product Surfaces And Experience

One typed application service projects the same kernel result to CLI, Python SDK,
schemas/conformance fixtures, optional stateless MCP or A2A adapters, and native
CI/forge carriers. A surface may adapt transport and presentation only; it cannot
recompile policy, retain lifecycle state, or invent a second error taxonomy.

The CLI defaults to concise human output and progressively reveals evidence;
`--json` is stable automation output, not a separate behavior. Diagnostics carry
one verdict, stable code, plain-language cause, exact evidence boundary, singular
next action, and user-decision flag. Adoption is plan-first and idempotent. The
installed product and contributor workflow both execute from an explicit
project-local environment and lock. Recovery starts from Git, OpenSpec, fresh
Facts, and Attestations rather than a surviving chat or proprietary agent state.

The terminal acceptance is task-based rather than screenshot-based: a new human,
an autonomous agent, and an SDK client can each inspect, adopt, prove, recover,
and uninstall a Python, polyglot, or docs/infra repository without learning ETHOS
internals, cloning this repository's layout, parsing prose, selecting among
equivalent commands, or contacting a forge for local validation.

### Feedback Intent Preservation

Convergence maps each accepted feedback item to an invariant, semantic owner,
acceptance, and proof—or records its explicit absence reason. Deletion is
preferred when that mapping shows a carrier duplicates another owner. No
historical wording is preserved merely to satisfy a text-shaped test.

### Bounded Change Convergence Route

This file owns the current dependency order above; archived Changes are evidence
of completed or abandoned work, never the current queue. Each batch receives one
coherent official OpenSpec Change whose `tasks.md` owns only that batch's
progress. A Change splits when its outcomes are independently useful or require
different owners, not because a file or line-count threshold was crossed.

Every implementation atom follows the same bounded route:

```text
fresh current facts
-> exact RED or missing-invariant evidence
-> one replacement owner
-> implementation and migration of unique semantics
-> deletion of the superseded owner and compatibility residue
-> repository-wide reference closure
-> focused proof
-> exact-HEAD full proof
-> official archive and post-archive proof
-> candidate and accepted exact CAS
-> runtime or projection readback when affected
-> lane, ref, worktree, and temporary-resource retirement
```

Re-plan only when a fresh accepted head or runtime invalidates the input, an
executable test disproves the stated model, an external stable dependency
changes, another live owner overlaps the same authority surface, an effect
outcome is unknown, or a declared resource budget is exceeded. New feedback is
mapped to the existing contract and current batch; it reopens source recovery
only when it demonstrates a missing or contradictory terminal invariant.

## Convergence Rules

1. **Promote before compatibility.** Replace a missing model boundary before
   introducing an alias, fallback, or shim; delete the residue in the same
   bounded change when proof permits.
2. **Compile, do not narrate.** Keep authority, bindings, invalid states, and
   effects in the owning contract and executable verifier; documentation links
   to them as a projection.
3. **Separate planes.** Local proof and each declared peer observation produce
   distinct attestations and cannot imply one another.
4. **Subtract before succession.** For every obsolete carrier or Work Lane,
   move only unique terminal semantics into the existing owner, then delete the
   implementation, tests, schema, documentation, state, ref, and worktree that
   no longer have a consumer. Foreign dirty work waits only for explicit owner
   handoff; it does not justify a preservation store or parallel lifecycle.
5. **Prove across shapes.** Product, code, and documentation adopters demonstrate
   the same input-to-verdict relation while retaining their native carriers.
6. **One obvious safe path.** Defaults select the least-powerful useful operation;
   advanced controls appear only when current facts require the distinction.
7. **Errors are continuations.** Every non-pass result preserves the diagnostic
   code and evidence boundary and identifies exactly one safe next action or one
   explicit user decision.
8. **Surfaces stay projections.** CLI, SDK, MCP/A2A, CI, forge, and generated
   scaffolds share contracts and conformance tests; none owns duplicate policy or
   durable progress.
9. **Close semantic increments.** Each phase produces an independently
   reviewable and provable terminal-state delta. Carrier topology follows intent
   cohesion and progress ownership rather than imposing one Change per outcome.
10. **Optimize verified semantic throughput.** Measure progress by accepted gaps
    closed per feedback cycle, not commands, churn, or raw test count. Repeated
    scans, broad discovery runs, oversized fixtures, duplicate runtime builds,
    false-green tests, agent rework, abnormal process loss, and unexplained
    latency are root-cause signals. Use the narrowest real reproducer and run
    heavy proof once at the frozen atomic boundary; never buy speed by weakening
    semantics, evidence freshness, coverage, or fail-closed admission.

## Completion Boundary

Terminal convergence is verified only when every batch above is accepted and
archived, exact-HEAD full proof and post-archive proof pass, candidate and
accepted refs complete their declared CAS transitions, and any affected
package/runtime is read back from its immutable installed form. Repository
semantic closure must report:

```text
missing=0
duplicate=0
orphan=0
superseded-active=0
conflict=0
```

Source, specs, schemas, tests, rules, skills, documentation, generated
projections, package/runtime, and configured provider surfaces must agree with
their unique owners. No active proposal, stale lane, dead-owner temporary root,
superseded runtime, or unconsumed evidence carrier may remain. Declared remotes
must point at the selected local OIDs and their hosted CI/signature state must be
reported separately and freshly; an undeclared remote creates no requirement.

A passing focused test, local architecture test, OpenSpec validation, package
build, or one hosted provider is never a terminal claim by itself. Any
unverified requested plane remains explicitly unverified and keeps the global
objective open.
