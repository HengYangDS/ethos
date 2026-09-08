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

Broad semantic recovery starts by declaring a finite source boundary in one
official OpenSpec Change. It preserves distinct obligations rather than message
count, adjudicates each as accepted, superseded, pending verification, or
rejected, and maps accepted meaning into this plan or another existing owner.
Raw transcripts, extracts, classifiers, and scratch matrices never become this
plan's inputs after that Change is proven and archived; their exact owned copies
are then deleted.

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
| Construction and dependency choice | handwritten orchestration, admitted dependencies, native language and platform facilities | Evaluate official and mature capabilities first. Admit a dependency, DSL, or framework only when it reduces total entities and maintenance; keep pure declarative compilation separate from bounded effects. |
| Collaboration and competition | concurrent Work Lanes, handoff, candidate selection, agent procedures | Coordinate overlapping semantic owners when cooperation avoids waste; permit evidence-producing alternatives when competition is justified; select or synthesize once, then retire losing and absorbed lanes without a persistent race ledger. |
| Learning and execution discipline | regressions, rules, repo-local skills, host memory, agent procedures | Repeated failures change the narrow product owner, regression, rule, or already-admitted skill. Optimize verified semantic throughput; memory and chat remain non-authorizing context. |

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

1. **Close design authority.** Reconcile every distinct obligation in the
   declared recovery boundary into the product contract, this plan, an existing
   executable owner, or an explicit non-current disposition. Validate the
   official OpenSpec Change; reject feedback-ledger roles; and remove any
   statement that makes archived tasks, chat, memory, summaries, or temporary
   extracts the current queue. Exit when the two canonical documents are
   complete and non-duplicative, the exact recovery inputs can be deleted
   without semantic loss, and no implementation or hosted-state claim has been
   inferred from design prose.
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
   exact execution facts plus a typed non-replaying continuation. Converge every
   dependency and embedded tool through one locked supply-chain source to the
   current upstream stable release. A hold remains an open gap, not satisfaction
   of the requirement; any exception requires explicit user approval. Prove
   that package/runtime/version output reports the selected OpenSpec and
   toolchain identities exactly.
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
6. **Close semantic and physical repository structure.** Reshape the whole
   repository by semantic ownership, not just the current Change or touched
   files. Apply the existing module-layout rule and deep-module obligation to
   source, tests, specifications, schemas, documentation, configuration, rules,
   skills, CI, and renderers. Establish responsibility, invariant, consumers,
   dependency direction, and reason to change before selecting a physical path.
   Group cohesive capabilities into semantic subpackages; prohibit suffix-flat
   sprawl, misplaced owners, and arbitrary nesting. Review complete capabilities
   and caller knowledge: absorb exposed internal sequences and duplicate
   decisions into their existing owners while retaining necessary authority
   inputs and genuine transport boundaries. Neither directory width nor depth
   proves good structure. Delete empty shells, unnecessary one-module packages,
   facades, and stale imports; retain a small namespace only for a demonstrated
   boundary. Move all consumers with each owner and retire its old path in the
   same bounded batch, without aliases. Reconcile documentation to one entrypoint,
   `guides/quickstart.md`, necessary READMEs, and a restored
   `docs/decisions/` containing only irreducible lowercase semantic records.
   Classify top-level evidence by real producer, consumer, binding, and
   retention; remove residue. Prove one quality owner per property, including
   docstrings, all meaningful tracked carrier formats, non-compensating
   per-owner budgets, modern Python within the supported floor, and native
   configuration placement. Verify that architecture and brand projections are
   faithful, accessible, navigable `信、达、雅` views rather than parallel
   ontology. Exit only after whole-repository ownership and dependency review,
   executable import/resource/link checks, behavior preservation, and projection
   readback find no missing, duplicate, orphan, superseded-active, conflicting,
   or misplaced owner. A clean file-count report is not semantic verification.
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
   accepted. Exercise the declared Python floor and current supported versions
   plus native macOS, Linux, and Windows adapters. Exit when every requested
   plane has fresh evidence and no adopter compatibility carrier or copied state
   machine is required.

Only disjoint read-only audits may overlap freely. Mutation that touches one
authority owner and its consumers is serial: one bounded official Change, one
owner, one accepted outcome, then cleanup before the next overlapping Change.
At the start of every batch, fresh facts may prove some work already satisfied;
that evidence closes the item without reimplementation. Reordering requires a
proved prerequisite, not convenience.

### Adopter Isomorphism And First-Hour UX

The product repository and adopters run the same kernel through profiles and
adapters, not product cloning. `status` is the read-only entrypoint; its current
result selects one continuation. `adopt` proposes an explicit binding to that
model; an absent optional carrier remains an observed profile fact.

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

Convergence maps each distinct obligation—not each repeated message—to one of
four dispositions: accepted, superseded, pending verification, or rejected.
Accepted meaning names an invariant, one semantic owner, acceptance, and proof.
Supersession applies only to the same subject. Pending items name the missing
fact or model gap and authorize no mutation. Rejected remedies retain their
rationale only in the governing official Change. Delegated observations are
separated from the reporter's inference and proposed remedy.

Deletion is preferred when that mapping shows a carrier duplicates another
owner. No historical wording is preserved merely to satisfy a text-shaped test,
and no transcript, memory, agent summary, classifier output, or temporary file
may become an active backlog. Recurrent execution failures are absorbed into
the existing product owner, regression test, rule, or admitted skill rather than
creating a feedback registry.

A concrete defect is evidence for a possibly general invariant, not permission
to narrow a general instruction to the reported file or current Change. First
identify its applicability and semantic owner, distinguish observation from
inference and remedy, and resolve contradictions or supersession on the same
subject. Then schedule bounded implementations in this route. Neither a local
fix nor a documented principle proves repository-wide fulfillment; each
affected surface needs its own evidence. Do not reopen already-settled product
decisions merely because a new example uses different filenames.

### Bounded Change Convergence Route

This file owns the current dependency order above; archived Changes are evidence
of completed or abandoned work, never the current queue. Each batch receives one
coherent official OpenSpec Change whose `tasks.md` owns only that batch's
pre-archive implementation and verification progress. Exact-current full proof
remains an executable archive precondition, not a checkbox assertion. Effects
that require the archive to exist remain pending here until their own evidence
is observed; putting those effects into the pre-archive completion predicate
creates a causal cycle. Archive alone never closes the implementation atom.
A Change splits when its outcomes are independently useful or require
different owners, not because a file or line-count threshold was crossed.

**Work Lane convergence is the highest delivery priority.** Only a demonstrated
prerequisite for safe absorption or retirement may precede it. Keep unrelated
features, supply upgrades, and structural refactors behind this priority rather
than expanding the current batch. Preserve live owners and unique dirty content;
priority never grants permission to bypass admission or weaken the 95-percent
floor.

Use current public capabilities to retire any lane already proven semantically
absorbed and safely deletable; do not make it wait for the entire product roadmap
or a runtime repair it does not need. For a lane that requires missing-Lease
reconciliation, first accept and read back that repair, then immediately absorb
and retire the affected resources. Order the existing inventory by demonstrated
readiness and dependency, close each outcome before opening another overlapping
one, and reuse an admitted lane. Measure progress by unique obligations absorbed
and exact refs, worktrees, Leases, and owned projections verified retired, not by
commits, tests, inventory passes, or documentation volume.

Housekeeping is part of each lane's closeout, not a later bulk sweep. Before
disposal, account for unique committed, staged, unstaged, and untracked meaning;
prove its absorption, supersession, or authorized rejection. Then retire exact
obsolete refs, worktree registrations and paths, Lease rows, and owned
projections through their existing public owners. Inspect the runtime, package,
supply, temporary, and generated resources that the retired lane produced or
referenced; preserve live consumers and required proof, and reclaim only what
has no remaining owner or retention obligation.

Post-observe both logical state and physical paths: no dangling references,
orphan coordination, stale launchers, broken links, abandoned temporary roots,
or unconsumed duplicate carriers may be hidden by a successful command. Moving
material into an ignored directory is preservation, not disposal or completed
housekeeping; its existing receipt must retain the reason and next disposition.
Use exact owned paths, bounded liveness checks, and safe handling of read-only
trees, never broad prefix deletion. Record any unresolved residue in this route
and its existing effect evidence, without creating a cleanup registry. A lane
is closed only when its semantic and resource obligations are both discharged.

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

OpenSpec implementation tasks cannot require their own archive or a later
accepted transition as an archive prerequisite. Keep those delivery obligations
in this execution route, explicitly pending until their effects are verified.
Moving a misplaced obligation here preserves it; it does not mark it complete.

Re-plan only when a fresh accepted head or runtime invalidates the input, an
executable test disproves the stated model, an external stable dependency
changes, another live owner overlaps the same authority surface, an effect
outcome is unknown, or a declared resource budget is exceeded. New feedback is
mapped to the existing contract and current batch; it reopens source recovery
only when it demonstrates a missing or contradictory terminal invariant.

The current bounded implementation is `coverage-floor-integrity`, reusing the
owned missing-Lease Work Lane. Missing-Lease reacquisition is implemented and
archived at `6db593c2`, but not accepted: its 93.15036-percent proof fails the
user-required 95-percent floor. The coverage repair below is now the acceptance
prerequisite. Neither coordination nor a successful dry-run proves absorption.

Last observed closeout evidence on 2026-09-07, not a second task system:

| Boundary | Last verified state | Required next evidence |
| --- | --- | --- |
| Repository proof | Accepted `18aa8707a48a686d4b59f4814d11eb95907c4e8c` has full proof Attestation `63cf3584ba37e221cbd952f7229f451dff865aadfcae7b55bbfe7fa902d79acb` | Reacquisition proof at `6db593c2` exists but fails the required 95-percent floor; reprove the corrected candidate |
| Archive and acceptance | `absorbed-resource-retirement` archived; candidate and accepted CAS completed; accepted effect `d8f0b37cc16a646ae4c5c215584c59cea4ba8726e0680e84cada147bff0c157e` | Reacquisition archive at `6db593c2` exists; coverage-compliant reproof and candidate/accepted CAS remain pending |
| Package/runtime | Selected runtime `9c3cf688` reports Alpha.5 source `18aa8707`, tree `45a6f84e`, OpenSpec 1.12.0, and four armed hooks | Accept and read back reacquisition before effects that require it; existing public retirement remains usable when its own preconditions hold |
| Peer projections | Publication `80833fbc8f556ec6e572e01f1f53b96c06ae58d12b35a06fc431b132c297b24f` binds both peers at `18aa8707`; exact dev/main readback agreed. GitHub dev run `34121912399` and main run `34121913185` subsequently failed. The dev receipt reports proven execution but blocked before/after readiness; GitLab CI/signature remain unobserved | Resolve hosted checkout/readiness obligations separately from executed proof; inspect exact run artifacts rather than reused runner paths |
| Lane residue | Retirement receipt `144d3ef4ee6af8407e188531106b91909181e11f3ea7b3ee8efaa0ee1bb76d8c` proves the previous implementation worktree, ref, and Lease absent; seven historical worktrees remain, five dirty | Prioritize proven-safe public retirement; accept reacquisition for lanes that need it, preserve unique content, and prove absorption before disposal; no bulk merge or dirty-tree deletion |

Historical work remains finite and classified by obligations rather than commit
count. These are observed disposition boundaries, not claims of completed
absorption:

| Historical resource | Semantic disposition and next evidence |
| --- | --- |
| `20260818-openspec-19-archive-owner` | The 1.8-to-1.9 supply upgrade is superseded by accepted 1.12; reject restoration of archived Commitment. Preserve valid no-spec and locked-supply obligations in their current owners before removing the ten dirty/staged paths. |
| `codex-contracts-land-test-refactor` and `codex-lifecycle-hardening-test-refactor` | Overlapping histories must not be merged wholesale. Cross-worker immutable supply reuse, worker long-tail scheduling, and cheap non-archive fixtures need current-owner evidence; obsolete Commitment/rebind code must not return. |
| `20260810-public-test-boundaries` | Preserve public Git preimage, out-of-scope-write, committed-effect diagnostics, and lock-after-observation race coverage. Reject the retired mutable ref-intent representation; prove scenario equivalence before disposal. |
| `20260810-coverage-source-policy-matrices` | Nine added definitions match current AST; one differs only by the current reference-owner name. Four historical boundary probes pass against the current owner. The npm distribution-allowlist assertion is restored in the unaccepted reacquisition candidate; obsolete contributor roles are superseded. The three dirty files remain intact until legal reconciliation and retirement. |
| `20260810-coverage-public-failure-matrix` | Nine dirty items, including untracked tests. Their unique failure scenarios still require comparison with current owners; ancestor HEADs do not prove dirty-content absorption. |
| `20260811-repository-transition-model` | Fresh CAS/Attestation, local-or-multiple-peer topology and minimal-entity intent remain valid; persistent Commitment roots and historical scope/Lease bindings are superseded. The 341 dirty items are not yet semantically adjudicated. |
| Unlinked `codex/openspec-19-archive-owner` ref | Retired through the accepted public owner; Attestation `067dd0dabfb6b6b6a5e6603c14ea84df11a026da6e8b0a0c7e0f72226b6a92bc`. Its absence does not retire the distinct dirty linked OpenSpec lane. |

The one current implementation lane exists because the historical roots cannot
grant current prewrite admission. It repairs missing coordination rather than
creating another preservation store. Once its immutable runtime is accepted,
re-observe the source-policy lane first, reacquire only its missing relation,
and separately admit reconciliation of the already-compared dirty content.
Proceed to public-test-boundaries and its unresolved lock-after-observation
cases, then the remaining finite historical resources. Reuse an admitted
historical lane where feasible; do not create one successor lane per residue.
Dirty-overlay disposal and semantic absorption remain separate proof boundaries.

### Coverage Requirement Repair Before Acceptance

The 2026-09-07 requirement audit supersedes any inference of compliance from
historical 93-percent proof. Commit `efa43b9f` lowered the executable floor;
current archived missing-Lease HEAD `6db593c2` measured 93.15036 percent and fails
when evaluated at the required 95 percent. Its archive and proof observations
remain evidence, but neither authorizes candidate/accepted advancement under
the corrected requirement. Accepted `18aa8707` and its runtime are unchanged.

`coverage-floor-integrity` reuses the owned missing-Lease Work Lane and the
existing quality owners. Execute in this order:

1. Watch the real gate incorrectly accept a below-required measurement, then
   restore the sole hard floor and enforce it in default/full proof and local CI.
2. Align the contract, config guide, quality skill, and official quality delta;
   remove the aspirational split and pre-existing-debt acceptance exception.
3. Close missing behavior using current coverage evidence and substantive
   assertions; consolidate repeated fixtures without dropping unique scenarios,
   excluding product code, disabling branches, or relaxing any budget.
4. Obtain focused GREEN, reference closure, unchanged source budgets, and one
   frozen exact-HEAD full proof. Archive/reproof must satisfy at least 95 percent
   before the existing public candidate/accepted CAS and runtime readback.
5. Resume the historical-lane absorption order above only with that accepted
   runtime. Hosted topology/signature, adopter conformance, and the other global
   batches remain independently unclosed.

The 2026-09-07 behavior batch extends candidate CAS/projection recovery and proof
issuance/persistence in their existing test owners. Real Git assertions preserve
ref progress after projection failure, exact replay, Attestation idempotence,
and dirty-overlay protection. Proof cases reject changed branch/HEAD, unresolved
authority, mismatched policy, and malformed artifact persistence. Shared fixture
consolidation preserves the previous scenarios within the unchanged test budget.
These are focused observations, not an exact-HEAD repository proof. The combined
diagnostic runs reach 107 previously missing line/branch obligations; at the
unchanged baseline denominator, at least 361 more remain before 95 percent could
be established. Do not merge diagnostic databases into acceptance evidence.
Continue with archive, runtime selection, retirement, and scope failure owners;
freeze and remeasure the complete declared product before closeout.

Archive fixture consolidation exposed a real deletion-boundary defect: changing
an empty receipt-path fixture into an absolute repository-root path returned `.`
as the compensation target. Dedicated isolated regressions subsequently proved
root deletion and symlink following, mismatched archive binding, and false clean
compensation with retained unowned content. Close these in the existing archive
parser and Git effect owner before resuming runtime coverage. Preserve the empty
receipt case, exact failed-command compensation, and collision preservation;
validate the real Git poststate rather than accepting a mocked cleanup call.
The bounded lifecycle set passed 102 tests; after preserving public collision
outcomes and adding an archive-shaped symlink case, the final three-file safety
set passed 74 tests. Six executed coverage-contract regressions also passed.
These remain working-tree focused observations, not exact-HEAD full proof.
This safety work neither lowers the floor nor establishes current full coverage.

The next runtime-selection batch preserves package authentication under the real
selection lock, exact command projection, stale-CAS refusal, compensation and
selector-byte preservation, linked or invalid coordinates, release attestation
and closure uniqueness, and read-only legacy migration rejection. Consolidated
setup removes repeated materializations without removing those assertions. The
four-file runtime/hook set passed 86 tests; the two selected files passed 26
tests with 98.27-percent local selection-module coverage. Isolated removal of
the CAS guard or legacy schema guard makes the corresponding test fail. These
diagnostics reach 23 additional baseline obligations beyond the prior 107; the
archive fix changed production code, so neither that sum nor any combined
historical dataset establishes current whole-product coverage. The test budget
was exactly 38300/38300 at that batch. The following retirement batch replaces
mocked coordinate compilation with real divergent Git/Lease fixtures, preserves
partial-effect recovery and repeat execution, and checks terminal receipt
contents through the public recovery result instead of a separate persistence
fixture. Invalid branch role, absent coordinates or accepted checkout,
non-divergent histories, ambiguous or dirty worktrees, missing or foreign
Lease authority, malformed reasons, wrong receipt mode, and stale execution
coordinates are rejected without changes to refs, worktrees, content, or Leases.
Receipt tests preserve repository binding, digest validation, missing/tampered
bytes, and invalid JSON/schema rejection.

The two retirement files passed 48 tests; the retirement and quality-contract
regression set passed 169. Local diagnostic coverage is 97.74 percent for
abandonment and 97.83 percent for operation, not whole-product coverage. Isolated
in-memory removal of the holder or execution-root guard makes its regression
fail. Moving terminal-receipt assertions into real recovery and consolidating
repeated setup removes 34 net physical test lines; the enforced test budget is
38296/38300. The observed global baseline remains the unchanged `6db593c2`
dataset. Continue with measured uncovered behavior, preserving unique scenarios
and the existing budget; then freeze source for a fresh full proof. No focused
dataset, arithmetic extrapolation, or old proof establishes 95-percent product
coverage. Archive/reproof and accepted/runtime advancement remain pending.

The scope batch retains exact metadata-only bootstrap, official validation
repair, missing/linked/ambiguous output rejection, and accepted-root unknown
intent behavior. It adds independently selected invalid command observations,
incomplete artifacts, foreign Commitment identity, and committed-source failure
cases through the current resolver, without a new scope carrier. The selected
file now has 80 cases; the five-file admission/OpenSpec regression set passed
103 tests. That set measures 98.07-percent local scope coverage, not global
coverage. Isolated removal of validation-observation or Commitment-identity
guards produces the expected refusal-regression failures. Consolidation removes
22 net test lines; the enforced test budget is 38288/38300. Product code and the
native coverage denominator are unchanged in this batch. Continue with the
uncovered runtime activation/materialization failure behavior; retain the full
95-percent acceptance hold and do not merge diagnostic coverage databases.

The Python-image batch replaces copy-call-only mocks with exact copied-byte,
source-permission, and relative-link assertions. One real image-copy fixture now
owns package/lock source identity, dependency absence, missing interpreter,
non-relocatable source refusal, writable installation over a read-only copy,
residue removal, and console-script regeneration; its previous effect-file
scenario is absorbed rather than retained in parallel. Interpreter discovery
proves offline, installed-only, invoking-Python execution with ambient virtual
environment removal; incongruent candidates cannot precede the valid image.
Windows layout cases exercise native directory/DLL copying, and the generated
POSIX launcher executes with spaced arguments preserved. These are bounded
fixtures, not proof of complete native Windows execution or crash scavenging.

The eight-file materialization/hook regression set passed 143 tests. Local
coverage measures 97.46 percent for Python environment and 97.77 percent for
Python image. Isolated removal of runtime-kind congruence or wheel identity
checks causes the intended regression to fail. The three test files lose 29
net physical lines while preserving source identity and cleanup scenarios;
the enforced test budget is 38298/38300. Product source, coverage policy, and
the old full dataset remain unchanged.

The activation batch consolidates linked-worktree setup while preserving common
and per-worktree configuration restoration. Native configuration drift, unreadable
observations, invalid admission inputs, and stale post-observed bindings are
rejected. Compensation attempts every recorded worktree, the common config, and
the selector even when individual restoration fails; exact selector CAS now
executes rather than only recording a mock call. Cleanup failures preserve the
activated runtime and report deferred removal or lost retained generations.
These are isolated failure fixtures, not concurrent-process safety proof.

The activation, materialization, and coverage-contract set passed 185 tests.
Local activation coverage moved from 87.93 to 93.70 percent; neither measurement
is whole-product coverage. In-memory removal of common-config validation or
premature termination of worktree compensation makes the intended regression
fail. The test file loses eight net physical lines; the test budget is
38297/38300. A temporary test failure assumed an empty fixture root; comparing
its actual before/after state corrected the assertion without changing product
behavior. Product source, native coverage configuration, and the historical
full dataset are unchanged in that batch.

Consumer-boundary regressions then exposed three genuine deletion defects:
nested directory links were filtered before validation, dangling root links
were treated as absence, and unreadable directories were silently omitted. Each
case deleted an isolated runtime sentinel under the previous implementation.
The existing observer now uses non-following metadata, complete directory
iteration, and regular-file reads; every unknown input blocks retirement.
Native permission failure proves unreadable-directory handling on POSIX;
Windows junction observations are simulated, not native Windows proof. Static
observations do not close consumer-acquisition or filesystem races.

All three consumer roots share the same rejection matrix and retain readable
nested references. Consolidated state-failure and selector-recovery tests retain
their unique assertions, including native SQLite rollback and exact selector
CAS. The hook/materialization/coverage-contract set passed 264 tests; local
activation coverage is 94.43 percent. The repair adds 11 physical product lines
and removes 16 net test lines; test ELOC remains 38299/38300. The initial scanner
fault injector missed the cached native scanner; real isolated permissions,
not that ineffective injection, establish the third RED. Native coverage config
and old full evidence remain unchanged in that batch.

The supply batch proves complete-manifest validation before dependency copying,
Python identity and prefix separation, linked input refusal, copied-byte checks,
locked requirement export, and offline install ordering. Native-observer result
validation uses controlled subprocess responses, not a claim of rebuilding an
entire interpreter. Node cases preserve exact prepared-coordinate selection,
workspace metadata independence, production-only nested package projection,
invalid lock/declaration rejection, and undeclared-package refusal. The existing
fixtures are consolidated without dropping their earlier assertions.

The materialization/activation/coverage-contract set passed 237 tests. Diagnostic
coverage is 100 percent for dependency supply and 95.17 percent for Node supply;
removing the Python identity or lock congruence guard causes the corresponding
regression to fail. Two test files lose 13 net physical lines and retain the
38299/38300 test budget. Product code and measurement configuration are unchanged.
The installed accepted runtime still rejects the already-corrected retained
module identity during full-proof readiness, whereas the source CLI reports
only that execution is required. This is a verifier-version difference, not an
admission exemption. The current-source full proof has now completed at
`48d73d29fb3929d4254ff56997982a9b3ef22c15`, with the source unchanged throughout:
2345 tests passed, one skipped, and 24 of 25 gates passed. The sole failure is
`coverage-floor`. Its `proof:execution` Attestation
`38e5a82539c3663f79579662603e1ebaf7255c1327ca644d1ba386f19f27bde1`
has verdict `block` and mints no authority. Installation smoke passed and the
observed pytest temporary root was removed.

This complete measurement supersedes the older full baseline for selecting
work: 18947/19803 statements and 4955/5520 branches are covered, for combined
coverage of 94.38850057260198 percent. At this denominator, at least 155 more
obligations must be covered to reach 95 percent. That arithmetic is a planning
lower bound, not evidence that any proposed batch meets the floor. Exact proof,
JUnit, and native coverage evidence remain under the existing ignored
`build/evidence/quality/` owner, including
`coverage-floor-focused/full-proof-48d73d29fb39.json`.

The start-compensation batch then exposed destructive ownership confusion:
provenance, foreign-holder, and hook failures removed existing worktrees, and
hook failure revoked a reused Lease. Six isolated cases failed before repair.
Start now distinguishes acquired from reused Lease state and consumes the native
worktree effect's applied/recognized result. Only proved new resources may be
compensated. Unknown new paths and dirty projections retain their dependencies;
failed cleanup remains visible. The existing four-field Lease revocation owner
replaces the start adapter's duplicate three-coordinate SQL. No runtime schema,
registry, or recovery carrier is added.

The seven-file start/Lease/worktree/quality regression set passed 131 tests.
The start failure matrix has 25 cases and 97.31-percent local diagnostic coverage;
it does not prove the whole product meets 95 percent. In-memory restoration of
forced worktree deletion and expiry-insensitive revocation each makes the
corresponding regression fail. Consolidation preserves bootstrap, candidate,
minimal Lease, idempotency, topology, and runtime-refusal assertions while
removing net test lines. These synchronous tests do not establish crash recovery
or arbitrary concurrent filesystem-replacement safety.

The archive batch preserves the former descendant, exact refresh, unrelated
archive, changed-tree, fork, malformed nested evidence, source mapping, collision,
and profile scenarios while consolidating repeated graph construction. New cases
cover multi-edge chains, cycles, equally near attestations, incomplete evidence,
and failed ancestry observations. Native Git fixtures verify that postimage
observation preserves the real index, HEAD, and working contents; they exercise
exact relocation and committed-diff selection, not a new official CLI run.
Public command tests distinguish staged from active intent, preserve diagnostic
gaps, reject invalid coordinates before effects, compensate invalid native
output, and forbid rollback after ref advancement.

The seven-file archive/proof/quality regression set passed 183 tests in 273.67
seconds; its disposable root was removed. The two changed test files passed
87 focused cases. Local diagnostic coverage is 98.59 percent for archive intent
resolution and 97.82 percent for the archive command. In-memory removal of tree
congruence, tie rejection, or committed-effect protection makes the corresponding
regression fail. An initial fault harness omitted future-annotation semantics;
that harness error was corrected and is not counted as detected product failure.
One test expectation also incorrectly invented `not_available`; the existing
committed/not-required/retained outcome and no-rollback assertion are preserved.

Product source is unchanged in this batch. The tests lose three net physical
lines and 25 ELOC, leaving test ELOC at 38263/38300. Comparison against the
unchanged full source identifies 30 newly observed statements and 24 branch
obligations in these two owners; this diagnostic delta is not a merged dataset
or a claim of whole-product coverage. The full XML and JUnit hashes remain
unchanged. Detailed command and fault observations stay under the existing
ignored quality evidence owner rather than OpenSpec tasks.

Archive boundary tests are committed at `5dc63eef0`; its signature and committed
blobs match the tested hashes. The subsequent Git-effect evidence batch replaces
plan/validator stubs with real Git objects, committed repository identity,
TransitionPlan compilation, typed Attestations, and current-postcondition
validation. It preserves issuer, ambiguity, malformed-plan, recovery-membership,
and store-collision scenarios while adding exact candidate/ref/assertion
selection, failed observation, timestamp ordering, and storage-error propagation.
The focused set passes 36 cases and the related Git-effect/accepted/archive set
passes 140 in 17.44 seconds. Four isolated guard-removal faults are detected.
Production source is unchanged; 15 statements and four branch obligations newly
observed against the previous full report are diagnostic only. Test ELOC is
38293/38300 after splitting mixed failure stages and consolidating duplicate
positive fixtures; an intermediate 38301 result was rejected, not grandfathered.

Post-commit runtime observation uncovered another boundary: two foreign-created
untracked browser logs in the canonical accepted checkout change its build
overlay while accepted commit/tree remain unchanged. The installed runtime's
expected-build observer consequently reports source/build unavailable and
package-entry prewrite reports root-binding mismatch. Do not delete unknown
owners' files, reinstall an identical runtime, or bypass hooks. The unchanged
source entrypoint admits exact-root/path test writes, but that does not prove
installed hook recovery. One normal signed commit attempt was rejected by
pre-commit with `root_binding_mismatch`; HEAD remains `5dc63eef0`, and the tested
files remain staged. Do not replay that mutation until its preconditions change.
An isolated repository reproduces the same error from one untracked observation
file with accepted commit/tree unchanged; the fixture and its log are removed
after recording the result in the existing ignored quality evidence owner.
The accepted-object repair now derives expected commit, tree, and raw canonical
version bytes from the accepted Git objects; checkout overlay remains a build
input, not acceptance identity. Isolated untracked/staged/detached cases failed
before repair; a separate CRLF case failed before binary blob observation. The
latest runtime/coverage-boundary set passes 24 tests with tested bytes unchanged.
Source status passes, but the installed runtime still reports expected-source
and expected-build unavailable. Its hooks have not been replaced and normal
commit remains blocked. No acceptance or installed-repair claim follows from
source-only GREEN. The two unknown-owner browser observations remain untouched;
a narrowly specified preservation relocation has been requested, not applied.

Coverage examination also exposed a fabricated coordination queue: four-field
Leases have no issue time, and no current consumer establishes queue membership.
A full projection regression rejected the stale age/order fields. The existing
owner and planning caller now omit them, retaining unknown/deferred-scope
precedence, overlap coordination, independent disjoint work, and candidate lag
or stalled-progress advisories. Collaboration and competition remain supported;
no scheduler, queue record, replacement registry, or Lease field is introduced.
The coordination/terminal-surface set passed 100 tests.

Git-object regressions preserve signed authorization, confirmation, signature
status parsing, invalid keys, and both anchor-CAS failure stages. They now assert
protected external-anchor requirements, failed native observation, unchanged
anchor bytes, and temporary-file cleanup through existing public owners. A fault
injection initially intercepted object-type discovery rather than raw commit
reading; narrowing its exact argument boundary corrected that test error, not a
product defect. Repeated trust setup and an unnecessary signed-commit content
fixture were consolidated without removing their assertions. Test budget
violations were rejected; the current total is exactly 38300/38300. The final
Git-object/coordination/post-archive planning set passed 95 tests. These native
Git/OpenSSH fixtures touch no workstation trust anchor. No Git-object production
change was needed, and neither focused set proves whole-product coverage.

The final seven-file runtime/Git-object/coordination/planning set passed 149
cases in 7.81 seconds; fixture roots were removed. Invalid-key and unsigned
refusals retain their earlier dry-run boundary rather than only testing apply.
Three in-memory faults are detected: removed unknown-scope precedence, missing
object-ID congruence, and omitted final anchor CAS. Source-wide types, scoped
Ruff/types, official OpenSpec, and Markdown validation pass; repository reference
closure reports zero findings. Live source `plan --changed` passes and its actual
payload retains conflict coordination and candidate-stall evidence without a
queue. Full coverage XML/JUnit remain unchanged and are still bound to the older
94.3885-percent proof. Focused coverage was isolated and discarded, not combined.

The subsequent bounded verification adds native Git object-kind, tag-peeling,
and missing-tree refusal cases. No Git-object production behavior changed;
existing signature-status and fixture construction were consolidated without
losing their assertions. Design-integrity testing exposed a real diagnostic
failure: after identifying a missing canonical owner, the axiom check reread
that file and raised instead of returning the blocking finding. The existing
owner now uses its already observed document set. Tests distinguish an absent
tracked document from an existing untracked document for every required design
carrier. A vacuous check naming the already archived topology Change was removed;
the general test still checks every current official Change's artifact shape.

The root README and engineering axioms still asserted persistent Commitment,
contradicting the canonical transient model. A regression failed before those
two projections were corrected; no second semantic contract was added. The
final eight-file design/Git-object/runtime/coordination set passed 175 tests in
15.43 seconds, with unchanged tested bytes and removed disposable roots. Three
additional fault injections detect absent peeled-commit validation, absent tree
validation, and suppressed missing-owner diagnostics. Test ELOC is 38299/38300;
intermediate overflow was rejected, not accepted. Product-wide types and scoped
Ruff/types pass. These remain focused observations; the previous complete
coverage XML and JUnit hashes are unchanged and no dataset was merged.

The user-authorized preservation moved the two exact browser outputs into the
existing ignored runtime work directory without overwriting content. Their
hashes, inode identities, modes, and modification times remained unchanged;
the accepted checkout became clean and installed-runtime status passed. This
unblocks normal commit admission but does not deploy the source repair. The
exact operation is recorded in `accepted-browser-preservation.json` alongside
the focused evidence. No hook was bypassed and no runtime was activated.

After preservation, 242 related tests passed; their disposable root was removed
and the previous full-coverage evidence remained unchanged. A broader type probe
found 12 diagnostics in unchanged CI tools, outside the current provider's
`src` target. Keep this quality-surface gap pending; a passing product type gate
does not establish repository-wide typing. The exact diagnostics remain in
`object-design-preserved-checks.json`; do not expand this frozen source batch.

The frozen batch was committed normally at `28ab608c`; the lane-priority plan
followed at `019f5198`. Complete proof of that exact HEAD finished on
2026-09-08: 2509 tests passed, one skipped, and 24 of 25 gates passed, including
installation smoke. Its sole failure is the coverage floor: 19015/19791 lines
and 5003/5518 branches, or 94.89904776956814 percent combined. Attestation
`4cc66b70d4ebc6c1c48cf687324a4e85fd953def14671cdc0dd1db22e3ef02e7`
is blocking. The source stayed clean and unchanged; the pytest root was removed.
This supersedes the older measurement, not the 95-percent requirement.

Consumer analysis then found a disconnected retirement observation/terminal
chain alongside the current typed transaction observer, and an unused Lease
projection helper. Remove those dead implementations, not their coverage
obligations through exclusions. The still-used Git reader keeps its exact
empty-output versus failed-observation distinction in the existing retirement
effects owner; its three consumers use that owner. Six affected files lose
77 net physical lines. The six-file retirement/Lease set passes 159 tests;
its disposable root is absent and full coverage/JUnit evidence is unchanged.
Ruff, product types, and official strict OpenSpec validation pass. An expanded
type check finds ten diagnostics in the touched linked-retirement test file;
the exact HEAD baseline reproduces all ten. They remain a quality-surface gap,
not a new regression or permission to claim repository-wide typing passes.

The nine dirty/untracked failure-matrix paths have a bounded semantic comparison
in `historical-failure-matrix-audit.json`. Gate, hook, CLI request, worktree
compensation, and newly added Git-effect scenarios have current counterparts;
public Lease storage-error propagation and mixed-state projection were the
remaining test correspondences addressed below. Preserve the original paths
until all remaining obligations and public disposal admission close. The clean historical lifecycle branch's
accepted-runtime retirement dry-run returns `work_lane_not_merged`; no effect
was applied. Cleanliness and AST/name correspondence alone never prove absorption.

The two previously preserved browser files contained only a generic GitLab
welcome and an unauthenticated login page, not CI/signature evidence. Their
hashes and no-open-reference checks passed before exact deletion; the empty
original directory is also absent. Other runtime work entries are unchanged,
and accepted remains clean. The existing preservation receipt now records
their final disposal and the retained observation, without another carrier.

The public installed-runtime refresh subsequently rebased all 19 lane commits
onto accepted `ca8f8110`, producing `3467aef5`. Every range-diff entry is
equivalent; local signatures verify, the candidate is an ancestor, the checkout
is clean, and installed-runtime status passes. This is a base-alignment result,
not new proof. The peer's additional tests raised merged test ELOC to
38312/38300; the budget correctly blocked. The current absorption batch removes
duplicate retirement setup, parallel import bindings, and repeated outcome
assertions without dropping their policy, ordering, receipt, or failure claims.
It adds historical missing/uninitialized/mixed Lease observation and public
SQLite/value-failure scenarios in the existing test owner. Current typed
request validation owns malformed-holder rejection; old migration-guard and
payload-binding tests cannot be restored as current runtime requirements.

The 203-test Lease, retirement, CLI, and schema focused set passes. Source and
both changed test owners pass typing, Ruff, and formatting. The isolated test
root is removed and all nine historical source hashes are unchanged. Test ELOC
is back within 38300 without changing its policy; two further assertions retain
the exact missing-control-root gap, not merely subset membership. Evidence is
in `lease-historical-absorption-focused.json` and its bound log; local coverage
is diagnostic only and used different options from the full proof.

Full proof of frozen `62e95342266b97c092dd9e4b20e878172b17453e` completed on
2026-09-08 with all 25 gates passing: 2518 tests passed and one was skipped.
Native coverage records 19016/19762 lines and 5008/5514 branches, or
95.04668460199399 percent combined. Attestation
`1d7605fd72de820d1cf8d24f6b0c3449a9d379b23338ce370b4b044be1df9984`
binds that exact HEAD; source remained clean and unchanged throughout execution.
The pytest root and owned proof processes are gone. The existing
`full-proof-62e95342266b-process.json` receipt binds output hashes and terminal
status; `full-proof-62e95342266b.json` retains every gate result. No focused
coverage was merged, exclusion introduced, or threshold or budget relaxed.

The post-proof check of all 53 changed Python files initially reported 96 type
diagnostics in `coverage-atom-changed-typing.json`. That same command now passes;
the production gate alone checks `src` and did not establish this wider result.
Seventeen existing test owners now use accurate fixture types, explicit shape
checks, and the current immutable contract. Deliberately malformed official
reports remain untrusted inputs; no production signature, policy, exclusion,
ignore, or type suppression was relaxed. Duplicate metadata construction and
recovery forwarding were removed without deleting scenarios. A too-narrow
`dict` assertion introduced during this work failed against correct immutable
facts; `Mapping` narrowing repairs the test, not production behavior.

The final archive, resolution, proof, and reference-closure set passes all 254
tests. Earlier runtime and retirement sets passed 149 and 78 tests respectively;
their recorded source hashes still match. Ruff, formatting, the exact 53-file
type command, repository audit, and semantic-reference closure pass. Test ELOC
is 38296/38300, with product and tool measurements unchanged. Temporary test
roots are removed; native full-proof coverage and JUnit hashes are unchanged,
not merged with these focused runs. `typed-authority-closure.json` and the
`typed-runtime-focused.json`, `typed-retirement-focused.json`, and
`typed-closure-reference-closure.json` receipts bind these bounded results.
Task 2.2 is closed. Whole-repository typing, including other CI tools, and
historical public schema-recovery correspondence remain separate open gaps.

The public land dry-run selects official Change archive as its next operation.
Archive then rejects the self-dependent task 3.2: it required that very archive
and later acceptance before permitting archive. The duplicate task is removed,
not checked off. Its unchanged delivery obligation remains **pending** here:
archive through the official owner, reprove, complete public candidate/accepted
CAS, and read back the immutable runtime. The two-file task/plan correction
changes the proved HEAD; obtain current proof before executing archive. The
zero-effect rejection is recorded in `archive-62e95342266b-dry.json` and its
cause in `archive-task-cycle.txt`. Accepted `ca8f8110` still carries the old 93-percent
policy until this correction lands. Runtime activation, hosted proof, historical
lane retirement, and supply upgrades are not established by this local proof.
Do not replay old coverage against shifted source lines or terminate another
lane's live proof for cleanup.

The structural obligation above is global and remains open. Reshape semantic
owners while absorbing historical lanes, then finish the remaining repository
boundaries in independently provable batches; do not expand the coverage Change
into an unbounded relocation. The latest worktree observation contains seven
historical roots, this owned lane, and accepted/candidate projections. An
independently created abandonment-recovery lane appeared and then disappeared
during observation; neither action was this thread's work.

The repository-wide Markdown audit parses all 1912 tracked files. Nine lists
mix sibling spacing: two in current content and seven in historical records.
Twenty-three single-paragraph lists use separators, of which 21 are historical.
The existing native lint accepts the mixed-list reproducer; successful syntax
checks therefore do not prove editorial consistency. The documentation policy
now states the structural rule, and the two current corrections remove only
five blank lines. Historical findings remain unresolved and byte-preserved.
The exact inventory and source hashes are in `markdown-list-audit.json`.

Close the systemic gap in the existing tracked-format owner and Markdown check,
using the already locked CommonMark parser, not another formatter or registry.
Enumerate tracked Markdown independently of directory; report immutable findings
through the existing lifecycle policy. Require boundary regressions for compact
and compound lists, nesting, blockquotes, code literals, and current/immutable
carriers, then re-audit all paths and verify content and block preservation.
This is pending implementation, not a completed gate. Creating a second active
Change caused `openspec_active_change_ambiguous`; the five self-created untracked
artifacts were withdrawn exactly, with their contents preserved in the audit
receipt. Do not create another lane or bypass this unresolved selection boundary.
After the coverage atom closes, keep this bounded successor ahead of the next
documentation-producing implementation batch. The supply successor below has
priority over unrelated new implementation; neither expands coverage scope.

### Latest-stable supply convergence

The 2026-09-08 read-only audit at `afe52d9` queried official metadata for all
72 Python and 150 distinct npm packages resolved in the locks. All requests
succeeded; this establishes observed versions, not installation or security.
The latest user requirement supersedes the previous default-with-hold wording:
latest stable is mandatory, and an unresolved constraint remains unfinished.

| Surface | Observed selection | Required disposition |
| --- | --- | --- |
| Cyclopts | Lock and installed runtime use 4.24.0; PyPI offers 4.25.1. | Update declaration and lock together; verify public CLI grammar and lifecycle commands. |
| shfmt-py | Lock uses 4.1.0; PyPI offers 4.2.0. | Upgrade through the existing dependency owner and verify actual formatter identity and shell checks. |
| ty | Lock uses 0.0.78; 0.0.79 is available, but upstream explicitly remains Beta. | Do not label the version bump stable. Establish a stable replacement in the existing type-check owner, or report the unsatisfied requirement; do not run parallel checkers indefinitely. |
| Python interpreter | Owned environment and accepted runtime execute 3.13.15; Python publishes stable 3.14.7. | Converge the default build and installed interpreter without dropping supported-version tests. |
| Embedded Node | Latest wheel wrapper 24.19.0 embeds Node 24.19.0; official stable is 26.8.1 and LTS is 24.20.0. | Resolve the package-runtime supply boundary; reuse the existing Node selection rather than hiding drift behind wrapper freshness or ambient PATH. |
| Python transitive closure | Latest Pydantic 2.13.5 requires exactly pydantic-core 2.46.5, while standalone core 2.48.0 exists. | Preserve the upstream constraint; do not force 2.48.0 or claim every transitive component is latest. |
| npm closure | All five direct selections match publisher `latest`; 53 transitive package names have at least one older resolution. | Refresh compatible resolutions and identify upstream constraints before any major-version replacement. |
| CI and downloaded tools | Five Action pins resolve to their latest release commits; declared uv, Syft, lychee, gitleaks, and actionlint versions match official latest releases. | Retain exact pins; artifact-hash validation, image freshness, and executed provider identities still require evidence. |

A dependency-only universal Python resolution succeeds and selects the new
Cyclopts, shfmt-py, and ty releases while retaining Pydantic's exact core pin.
It is not regenerated project-lock or stable-lifecycle evidence. The npm lock
edge check finds 75 references whose latest target satisfies the parent range
and 59 whose latest target does not; these are references, not package counts
or proof of a globally solvable update. The failed root `uv --no-build` probe
only prevented dynamic project metadata generation. The sparse `npm outdated`
result lacked installed versions and did not audit the transitive closure.

The source declarations, locks, environment, and immutable runtime are unchanged.
Evidence remains in the existing `build/evidence/quality/coverage-floor-focused/`
receipt directory: `supply-freshness-20260908.json`, the corrected
`supply-runtime-freshness-20260908-verified.json`,
`supply-stability-classification-20260908.json`,
`supply-python-resolution-20260908.json`, and
`supply-npm-constraints-20260908.json`. Their source URLs, observation times,
input hashes, and limits support this dated assessment, not future freshness.

The 03:14-03:17 UTC publisher recheck confirms the wrapper still supplies Node
24.19.0, behind both Current 26.8.1 and LTS 24.20.0. Node recommends LTS for
production; channel suitability must be explicit rather than inferred from
version ordering. The ty README still declares Beta and no stable API. Pyright
is an unelected replacement candidate: GitHub's latest release is 1.1.412, but
native npm publishes 1.1.413 with a matching repository tag and no GitHub release
record. Do not call 1.1.412 universally latest or treat these surfaces as equal.
`supply-stable-boundary-recheck-20260908.json` retains the official responses,
hashes, unavailable guessed ty page, and unresolved artifact-selection boundary.

Complete the current coverage atom without dependency churn, then execute a
bounded supply successor through the current public lifecycle in the owned
lane; do not create another lane or simultaneous active Change. First close
stable-channel and embedded-runtime selection, then update native declarations,
locks, artifact hashes, and their generated consumers together. Verify the
affected CLI, type, shell, package, and runtime boundaries; freeze for full
proof with the unchanged 95-percent floor and source budgets. Accept and read
back the new immutable package/runtime before claiming upgrade completion.
Historical lane absorption remains high priority: retire already-qualified
residue without waiting for unrelated supply work, and do not add new lanes to
this queue. Supply work must not become a reason to defer semantic absorption.

Run one writer and at most one heavy proof. A regression exposing a new semantic
contradiction or a budget failure triggers owner-level replanning, never a
threshold reduction. This section owns execution order; the official Change
owns bounded task progress, and generated receipts own execution observations.

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
11. **Prefer proven capability over local machinery.** Inspect official carrier
    support, the standard library, platform primitives, and mature tools before
    custom implementation. Adopt only when the result removes more semantic and
    operational surface than it adds; otherwise keep the direct owner.
12. **Use collaboration and competition deliberately.** Coordinate overlapping
    owners by default. Run independent alternatives only for a named uncertainty
    whose evidence value exceeds duplicate cost, then select or synthesize once
    and retire the residue.
13. **Scale verification to the claim.** Independent verification is mandatory
    only for the risk or completion plane that selects it. It must remain truly
    independent when selected, but cannot become a universal duplicate
    implementation or default heavyweight blocker.

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
