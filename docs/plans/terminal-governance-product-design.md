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

The dependency-ordered destructive batches are:

1. **Close the active local repository-effect atom.** Remove the model defect
   that made lifecycle commands mirror Git and OpenSpec inside Lease state.
   Compile intent from the exact official OpenSpec Change, reduce Lease to the
   lane-holder relation, route remaining local ref effects through the common
   Git-effect owner, and delete tracked Commitment carriers plus private binding,
   receipt, predicate, recovery, hook authority, tests, and documentation in the
   same Change.
2. **Unify authority and result projection.** Replace command-local status,
   plan, prewrite, and hook interpretation with one resolver and closed result
   algebra; remove duplicate diagnostics and abstract next actions.
3. **Converge official projections and acceptance compilation.** Compile the
   minimal Commitment value from official OpenSpec requirements and scenarios;
   derive effect paths from fresh Git Facts; delete relation, predicted-scope,
   research, authority-reference, and progress fields that do not alter
   acceptance. Do not add a replacement carrier.
4. **Close coordination.** Build one positive lane/Lease reconciliation model
   for start, continue, handoff, takeover, reacquire, restore, absorb, preserve,
   and retire. Delete command-specific orphan ownership and model `unbound` as
   an observation rather than authority.
5. **Correct integration roles.** Keep authoring on `work/*`; project proved
   objects to `proposal/*`; converge developer MR/PR and maintainer exact-CAS
   paths on the same promotion semantics and cleanup.
6. **Close immutable identity and installation.** Establish non-reused package
   versions, source/tree/runtime digests, repository binding, package-only
   operation, idempotent hook/runtime upgrade, uninstall, and retention/GC.
   Package construction treats the exact Node lock as selection authority and
   one repository-prepared production tree as supply: Hatch validates and
   projects that tree directly into wheel and sdist, and never resolves or
   installs a second dependency closure during artifact construction.
   Runtime materialization preserves each standalone interpreter's native
   platform layout. Windows keeps `python.exe`, `Lib`, `DLLs`, and runtime DLLs
   at the interpreter root. The authenticated runtime Python plus
   `-B -I -m ethos.cli` is the sole internal ETHOS execution authority across
   runtime selection, generation checks, continuations, and Git hooks; package
   console scripts are not a second authority. No fallback path or compatibility
   wrapper is retained. Runtime materialization invokes the locked installer as
   `python -B -I -m uv`, so the package owns its platform-native binary discovery
   rather than ETHOS deriving a sibling executable path.
   Shared external process creation is owned by one provider-neutral adapter;
   Git retains only Git-specific resolution and failure classification. Windows
   runtime observation resolves PowerShell from the native `SYSTEMROOT` path,
   never ambient `PATH`, and preserves exact argv, cwd, and operating-system
   cause when creation fails.
   Runtime post-observation compares those prefixes by platform-native path
   identity rather than serialized separator or case spelling; exact GitHub
   Windows 3.12, 3.13, and 3.14 execution closes that hosted boundary.
7. **Complete assurance and publication.** Compile requirement coverage into
   proof obligations, separate local and hosted phases, admit independent
   verification, and prove local/GitHub/GitLab publication as distinct planes.
8. **Subtract operational residue.** Enforce semantic ownership, duplication,
   module boundaries, temporary-resource ownership, supply-chain integrity,
   and performance through one quality graph; delete obsolete code, tests,
   schemas, documentation, configuration, runtime generations, and refs.
   This batch remains independent successor Changes: hosted execution
   environment completeness (including identity-drop process availability),
   Windows native trust/ACL conformance, and dead-owner temporary-resource
   recovery with inode and cleanup budgets. None is absorbed into package
   supply or standalone runtime layout merely because hosted evidence exposed
   them together.
9. **Prove terminal slices.** Run greenfield, brownfield, package-only, local,
   single-forge, dual-forge, interruption, drift, unbound, and adversarial
   adopter workloads before claiming terminal convergence.

Only disjoint read-only audits and disjoint later-change preparation may run in
parallel. A mutation owner and its consumers converge serially so that no two
active Changes modify the same authority surface. Each batch starts from fresh
accepted-root facts and may be reordered only by evidence that its prerequisite
is already satisfied or invalid.

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

The completed convergence carrier is immutable history at
[`2026-08-16-model-promotion`](../../openspec/changes/archive/2026-08-16-model-promotion/).
Its archived
[`tasks.md`](../../openspec/changes/archive/2026-08-16-model-promotion/tasks.md)
records the bounded implementation and proof mapping. This plan owns no queue,
phase state, dependency ledger, or progress projection.

The implementation order is the order in that task owner. Small commits are
encouraged, but no parallel backlog may split semantic ownership. New intent
outside the current official Change waits for its own bounded official Change;
evidence that must survive is recorded as a non-authorizing Attestation.

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

Terminal convergence is verified only when the kernel, Git-native effect
boundary, open invalid-state handling, profile isomorphism, and projection
relations pass their owners' checks. A passing local architecture test is not a
claim of hosted publication, adoption completion, or historical archive repair.
