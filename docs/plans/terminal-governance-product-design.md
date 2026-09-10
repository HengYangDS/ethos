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

The bounded `reviewed-content-retirement` and `detached-reviewed-retirement`
implementations are archived and accepted at `95b6153b`. The active bounded
Change is `native-observer-socket-identity` in the same owned
`work/20260907-missing-lease-reconciliation` lane. The earlier disconnected
POSIX snapshot prototype remains withdrawn; its implementation is not restored.
The official Change instead binds reviewed dirty content, index and ignored
resources to the existing abandonment operation, with exact authority rechecks
and recovery. Neither Git ancestry nor an ignored path authorizes deletion.

The September 9 user decision resolves the native-unlink trust boundary:
all actual writers stop and honor lane coordination before destructive review
and disposal. Uncooperative same-UID writers are outside that guarantee.
Semantic acceptance, current authorization and verified writer quiescence remain
distinct prerequisites. This decision retires the unsupported isolation promise,
not drift rejection, active-consumer protection or interrupted-effect recovery.
No further snapshot passes, preservation archive or unrelated Lease-storage
consolidation belongs on this critical path.

The user also assigns every ETHOS lane to this conversation as the sole
convergence owner. Public accepted-runtime takeover moved the only other
recorded holder, `work/20260811-repository-transition-model`, from generation 1
to 2. `central-owner-takeover-post.json` verifies unchanged HEAD, tree, index,
all 341 changed entries, branch refs and worktree registrations. All four
existing Lease rows now name `codex:openai:task:01a00063-d09e-7a71-a52e-a663800a7a0f`;
two are valid and two expired at that observation. Missing-Lease and detached
historical resources remain centrally managed without manufacturing coordination
only to delete it. The predecessor handoff states implementation stopped and the
selected lane has no listed open-path references; this is cooperative evidence,
not OS-enforced isolation. Historical bytes still require reviewed disposal.

Historical pre-acceptance checkpoint: the bounded Change was committed at
`bafb51cb7`, but was not yet accepted at that observation. Its
implementation checklist is backed by the 325-case affected retirement set,
56-case Lease/CLI set and current 65-case ref-intent/hook recheck. All 28 changed
Python files pass Ruff, format and explicit typing; official strict Change
validation, docs registry, Markdown and independent source budgets pass. Public
command guidance now includes reviewed-content derivation and stopped-writer
preconditions. Exact-HEAD full proof, archive, acceptance, runtime deployment
and historical disposal are the next unproved effects; no checkbox claims them.

That first 24-gate full proof blocks in Attestation `4f8a3988d5ab7ad586969103fcda90a9184f68ea600a67413d9e3743a7ed3ba7`.
Both failing architecture tests and repository audit identify one cause: the
native `lsof` consumer is absent from the existing runtime executable declaration
in `system/surfaces.toml`. No second registry is needed. The complete test run
records 2754 passed, two failed and one skipped. Its measured combined coverage
is 95.16274333163605 percent, but failed tests prevent updating the HEAD stamp;
the coverage gate correctly rejects stale evidence rather than accepting that
number. `reviewed-content-first-proof-failure.json` binds the failed proof and
XML hashes. Correct the missing declaration, rerun the exact architecture
failures and audit, then freeze a new commit and prove it without weakening any
gate. The first proof remains failed; build and install-smoke passes are not
acceptance of this Change.
The declared executable correction passes both original failing architecture
tests, the complete repository audit and native configuration quality;
`reviewed-content-lsof-declaration-green` binds the exact inputs and confirms
test-root removal. No product code, gate, exclusion or coverage policy changed.

`git-native-evidence-retirement` is archived and locally accepted at
`bf825e26b07bb6353b8a0fc5777eed399eca3ee1`, tree
`23dce85e42a23a05c7ea61dca0e29b3e369edb78`. Its exact full proof has 24 passing
gates, 2562 passed tests and one skip; combined coverage is 95.15943295080014
percent. Attestation
`32b60d578a6c1520d0942617134faf1484233edd71a7b4154ec3bab0c77ddc23`
and accepted effect
`80b795d30b4f1b9f446ef37fd8baf6bb09119896246ff900e3f218afa8e14829`
record proof and delivery separately. The source delta from `06ea14f0` is 607
files, 782 additions and 30398 deletions. Both workspace evidence roots are
absent; Git-native Attestation selection and historical Git objects remain.
Earlier failed proofs remain failed observations, not the current verdict.

Historical pre-commit checkpoint: reviewed-content retirement was uncommitted.
The September 9 preflight correction uses the progress that admission actually observed instead
of an earlier duplicate observation. Its regression first reported stale
`ready` after preflight observed partial removal; `retirement-preflight-progress-red`
records one failure. The operation/native-worktree run then passed 68 tests.
Two intermediate failures exposed a fixture without its required actor and Git
root; the fixture now establishes both rather than bypassing preflight. `retirement-preflight-progress-final` binds the final 68-case result.
`retirement-progress-all-static` verifies all 17 changed Python files with Ruff,
format and typing; the documentation check reports zero Markdown issues. None
of these checks proves full current coverage.

`retirement-progress-full-affected` stopped at 22 passes and one native process
observation failure. A six-case isolated diagnostic passed, but rerunning its
preceding test sequence reproduced the failure. `native-observer-exact-frame`
captured a descriptor-only `f36` record belonging to a Chrome Helper; a subsequent
process-specific observation no longer listed that descriptor. The old lsof
field selection omitted the native error-name field. Apple's Darwin libproc
implementation positively distinguishes unavailable descriptors/processes from
permission and unknown errors; an owned socket-turnover experiment reproduced
that distinction. The observer now requests the field and admits only the exact
Darwin absence grammar after a valid process frame. Unknown, permission-denied,
orphan, malformed and non-Darwin diagnostic frames still block; an ordinary live
file with a diagnostic-looking name remains an identity-bearing consumer.

`native-observer-absence-parser-red` records three failures after the transport
correction; `native-observer-absence-green` records 32 passes after the parser
repair. `native-observer-retirement-focused` binds 100 passes across the real
retirement/process sequence, unchanged selected source hashes, and removal of
its owned temporary root. The September 9 readback independently reconfirmed
those hashes and the 68-case preflight receipt. These results close the
reproduced descriptor-turnover boundary, not restricted-visibility process
enumeration, an atomic global snapshot, arbitrary same-UID writers, native
Windows support, or full current proof.

Earlier `reviewed-disposal-boundaries` binds 41 passing hardlink, survivor-drift
and process cases; its unchanged selected source hashes remain valid, but it
does not bind the later executor correction. The earlier 61/213-case runs
precede later source changes and are not current aggregate proof. Every receipt
above is under `build/evidence/quality/evidence-retirement/`; owned diagnostic
temporary roots were verified removed. No current Change acceptance or
historical lane deletion occurred.

| Boundary | Verified implementation and evidence |
| --- | --- |
| Literal root identity | Reject symlink roots before resolution, missing targets before they become cwd, and replaced, locked or prunable roots as drift. `retirement-root-*` and `content-guards-*` retain RED and focused GREEN. |
| Reviewed preimage | Staged, unstaged, untracked and ignored content bind the exact tree, native index and literal link targets. Native coordinates are eight decimal strings, preserving canonical JSON rather than widening its numeric grammar. Compilation observes actual cleanliness, not constant `clean=true`. `content-identity-*` and `content-boundary-*` retain evidence. |
| Receipt grammar | Reject malformed nodes, noncanonical paths and symlink parents. Empty review content preserves historical no-review receipt bytes and digest. `content-contract-*` and `content-tree-*` prove grammar, not filesystem truth. |
| Native traversal | Open each ancestor without following links; use descriptor-relative reads, traversal and `readlink`. Two real root/parent substitutions are rejected without opening external files. Enumeration errors, nested repositories, FIFO and unsupported native capability block. `content-parent-*` retains the regressions. |
| Effect-time authority | Ordinary Git removal deletes ignored files without force. Recheck content, actor, Lease and accepted ref after native worktree observation, through the existing preflight callback. `content-effect-*` retains four real deletion failures and the repair. |
| Active consumers | Native process file identities protect cwd, open files, mmap after fd close and external hardlink consumers whose paths are absent from argv. All four originally lost the worktree; current regressions preserve it and allow dry-run recovery after consumer exit. Unknown, malformed, truncated or failed observation blocks. `content-consumer-*` includes the 214-test affected result preceding the next ordering repair. |
| Admission ordering | Two real cases added ignored bytes during the process scan or later Git admission; both old orders deleted them and returned retired. Complete Git admission, then process observation, then exact content verification. No product ELOC was added. `content-observation-window-*`, `content-git-admission-real-red` and `content-admission-order-*` retain RED, 10-case GREEN, static checks and the preceding 216-test affected result. A preceding probe failed from a test-local shadowed variable; it is not product RED. |
| Semantic consolidation | Native worktree parsing, terminal reporting, receipt execution and request compilation each have one owner. Abandonment and linked retirement share the existing compiler and executor without aliases. Admitted unbound recovery skips only absent-worktree cleanliness; present reviewed content still observes actual cleanliness. The unsafe-inventory sentinel now intercepts the compiler's actual dependency. `retirement-unbound-compiler-focused` and `retirement-compiler-convergence` bind 11-case and 213-case GREEN; the prior two-failure compiler run remains RED. |
| Failure evidence | Four regressions exposed lost command, cwd and cause after process/Git errors, including partial retirement and unavailable post-observation. Git now specializes the existing process error contract; retirement projects it through one failure owner instead of string-only duplicates. Product ELOC falls by 25. `retirement-process-evidence-red`, `retirement-process-evidence-affected` and `retirement-process-evidence-complete-checks` retain RED, 269 affected passes, current static checks and 14 hook passes after fixture typing repair. |
| Surviving registration | Content absence with exact Git registration is recoverable without force. Three RED cases exposed post-admission HEAD/branch drift and reviewed recovery requiring a vanished root. Native removal now rechecks registration after admission; reviewed recovery verifies the original surviving index. Changed or replaced index bytes, index links and recreated content remain protected. `reviewed-absent-recovery-*` retains RED, 116 affected passes and static results. This registration evidence predates selective disposal; neither it nor the later disposal excludes arbitrary concurrent same-UID writers. |

Selective disposal now precedes native deregistration: no-follow descriptor
traversal rechecks surviving identities, preserves the original index, unlinks
reviewed files and removes owned directories, leaving the Git marker until last.
Read-only directory repair never chmods shared file inodes. Hardlink recovery
accounts for missing reviewed aliases: device, inode, mode, owner, size and mtime
must remain unchanged; ctime may advance only with the exact expected link-count
reduction and unchanged content. External link-count/content drift still blocks.

A real interrupted-disposal regression showed index changes after the first
unlink were previously lost by native deregistration. The index is now checked
before each deletion and at completion. These repairs close demonstrated cases,
not the final check-to-syscall race or arbitrary same-UID concurrent writes.
The reviewed public path now covers missing/expired coordination. Remaining
mount/visibility boundaries and cross-platform evidence remain required;
snapshots are not isolation.

The September 9 native-unlink regression turns that limitation into two failing
public cases. A separate Python child writes new bytes or atomically replaces
the selected file immediately before the real unlink syscall. Both operations
delete the unreviewed bytes despite the previous content check.
`retirement-native-unlink-race-red` binds two failures, unchanged selected source
hashes and verified temporary-root removal. No historical source was used or
deleted. The later explicit user decision selects stopped, coordinated writers,
so this uncooperative-writer acceptance premise is superseded, not repaired.
Keep the RED receipt truthful; replace its unsupported guarantee with execution
coverage of writer exit, final-content review, exact disposal and recovery.

Native capability observations narrow the decision: moving a root leaves an
already-open directory descriptor usable; this process's file-lease attempts
return EPERM for a file and ENOTSUP for a directory. They do not establish a
portable exclusion primitive. Apple lsof source also distinguishes two facts:
`FD unavailable` and `process unavailable` encode EBADF and ESRCH, whereas its
process enumeration silently skips EPERM. The former are not evidence that
the parser currently ignores a permission-denied file; the latter disproves
inferring complete visibility from a successful lsof exit and empty stderr.
`native-lsof-visibility-research` preserves those exact upstream excerpts and
hashes. Do not delete the legitimate vanished-descriptor handling as a patch.

The confirmed boundary requires coordinated writer exit, not a new isolation
subsystem. No same-principal lock, path rename or process list proves arbitrary
same-UID exclusion. Unknown required liveness still preserves source bytes;
verify actual participants rather than treating the user requirement as an
observation that they have stopped. Current-head CI and signature closure
remains independent of this disposal work.

Native Git 2.55.0 also removes the linked-worktree admin directory and registration
after recursive content removal fails with permission denied, leaving ignored
bytes and the ref behind. `native-partial-removal-probe.json` records those exact
postconditions; `native-isolation-probe.json` proves writes through a directory
descriptor still reach a moved root. Content disposition must therefore finish
before administrative deregistration destroys recovery coordinates. Neither
moving the root nor another snapshot ordering is a complete disposal model.

Windows reviewed-content support and completeness of native process observation
under restricted visibility remain unproved. Runtime activation still consumes
command-text process observations; it has not adopted the new file-identity
observer. Reviewed missing/expired Lease admission now reuses the existing
holder decision and exact Git deletion boundary; it remains unaccepted. Read-only
cleanup must change only admitted owned directories, never external link
targets or shared file inodes; the existing runtime cleaner does not satisfy
that contract unchanged.

September 9 measurement including untracked source is product/test
39998/39969 after aligning retirement tests to the confirmed coordination
boundary. Both independent 40000 ceilings pass. The old native-unlink receipt
remains RED for its superseded isolation premise, not a repaired guarantee.
The existing live-consumer test now includes an actual writer that flushes its
last bytes before exiting: old reviewed content blocks, final-content review
permits disposal, and worktree, registration, ref and Lease are verified absent.
`coordinated-writer-stop-focused` records five passes with source hashes matched
and its owned test root removed. Product code is unchanged by this adjustment;
Ruff, format and explicit test typing pass. The retirement, native-process,
worktree and Git-admission affected set passes 325 tests in 298 seconds;
`coordinated-writer-retirement-affected` records matching selected source hashes
and removal of its owned root. Markdown validation reports no issues across
1638 selected files. This is focused behavioral verification, not full coverage,
acceptance, deployment or historical disposal. Exact-root admission first
moved product/test to 40019/39734; absorbing the forwarding-only failure-report
layer into its existing operation-local owner then removed 23 product ELOC.
The earlier 39997/39911, 39997/39873, 39996/39787, 39996/39734, 40015/39703, 40062/39645 and 40013/39640
readings are historical. `native-unlink-race-checks` records its earlier Ruff,
format, explicit test-file typing, Markdown, diff and budget results, not full
behavior proof. Two lines of product headroom do not establish sustainable completion. Do not
minify, weaken checks, exclude source or move semantics into an exempt carrier.
Remaining safety work must still fit; metric correctness and calibration are a
separate successor, not permission to relax this budget.

Retirement contention now uses nonblocking acquisition at the existing operation
owner. A held lock yields `lane_retirement_in_progress` and the original receipt
identity/recovery command, without fabricated observations or progress receipts.
The rooted RED timed out after ten seconds in the previous unbounded acquisition.
The first harness run failed before contention because its pytest rootdir was
wrong; subsequent intermediate failures were test expectations for a stale gap
and optional receipt metadata, not new production defects. Those failed records
remain failures. The eight-case regression covers apply/recover, dry-run/apply
and normal/killed lock-holder exit; it proves re-entry into current-state
admission, not successful disposal of its deliberately stale request.
`retirement-lock-contention-affected` binds 129 passing tests, unchanged selected
source hashes and removed test roots. State projection now reuses the existing
progress state instead of independently reconstructing it; this also removes
the brief 40001 product-ELOC overrun without changing the ceiling or exclusions.
This increment resolves unbounded retirement coordination, not arbitrary
same-UID filesystem exclusion. No historical lane was deleted or accepted by it.

The consumerless retirement reporter and forwarding-only readiness layer are
deleted. The single operation executor now owns its lock and request-bound
control root. Their focused receipts record 62 and 95 passes at their respective
source states. A later Unicode-key regression demonstrated that the private
receipt serializer disagreed with the kernel's request identity. Removing that
serializer closes the duplicate owner: `retirement-canonical-identity-red`
records the failure, and `retirement-canonical-typed-green` binds 96 passes after
the repair and test value narrowing. Ruff, formatting and Ty pass for those
touched files; the original ASCII historical receipt identity remains tested.

Eight injected native-stat cases showed that derivation accepted foreign UID
or device observations for a root, directory, file or index. The existing entry
observer now rejects those nodes before opening or descending, and effect-time
verification uses the same owner. `content-native-boundary-red` records eight
failures; `content-native-boundary-green` binds 29 passes including parent-swap,
literal-link, shared-file and interrupted-disposal regressions. Native files
and directories are used, but foreign ownership/device observations are injected;
this is not a mounted-volume or privileged ownership test. Same-device mount
aliases, restricted process visibility and arbitrary concurrent writers remain
unproved. Both focused runs verified source hashes and removed their owned test
roots. No full proof, acceptance or actual historical retirement follows.

Control and execution roots now share one native Git coordinate observation:
the selected absolute directory must be a non-link, non-junction exact worktree
root in the request's Git common directory. A real nested directory, injected
junction predicate and independent repository exercise both roles before any
carrier observation. `retirement-root-owner-red` records four failures and two
already-protected cases; `retirement-root-owner-green` binds 69 passing operation
and public historical-coordination cases plus unchanged source hashes and owned
temporary-root removal. This does not prove native Windows junction handling.

The absorbed-ref failure projection had two layers for the same operation: a
local closure forwarded eight existing context values to a private sole-consumer
reporter. The closure now owns that projection directly; the forwarding helper
is deleted, preserving fresh error inputs, mutation verdict and compensation.
The unchanged public absorbed-ref suite passes all 16 tests both before and after
the refactor (`absorbed-failure-owner-baseline` and `absorbed-failure-owner-green`).
Both runs bind source hashes and verify temporary-root removal; Ruff, format and
Ty pass. `absorbed-failure-owner-budget` records the passing independent budgets.
This is behavior-preserving consolidation, not a new product RED or evidence
that the complete retirement Change is accepted.

The reviewed-coordination increment first reproduced four public derivation
failures for missing/expired coordination while correctly protecting a live
foreign holder. Reusing `holder_gaps` exposed one remaining expired-Lease Git
admission failure. The shared Git boundary now requires exactly the coordinated
topic's nonzero preimage-to-zero update and the current receipt actor. A
21-case matrix exposed twelve previously accepted unsafe landed/retained-mode
shapes as well: ordinary updates, unrelated or additional refs, zero preimages,
and missing/foreign actors. Those negative cases now reject the effect.

Real hook fixtures then exposed two failures retiring pre-adoption history;
the existing absent-prestate deletion rule now covers abandonment, without
creating a profile in the historical tree. The public matrix verifies missing
and expired disposal, valid foreign-holder protection and post-derivation Lease
acquisition protection, both at accepted equality and a pre-adoption ancestor.
`reviewed-historical-hooks-green` records 46 passes before formatting;
`reviewed-coordination-affected` binds that increment's selected source to 297 passes
across retirement, Git admission, native worktrees and process observation.
Owned test roots were removed. Its static, official OpenSpec and Markdown checks
precede the later consolidation and native-boundary edits; they do not prove
the entire current source. No full proof or historical retirement is claimed.

Two preliminary fixture failures used a three-segment holder and an attribute
on a dictionary result. They are not product RED. Two diagnostic static commands
also guessed nonexistent/tool-incompatible config paths; the corrected calls
use the actual root Ruff config and repository-native Ty invocation. These
failures reinforce reading the owning entrypoint instead of inferring it from
directory names. The canonical regression also initially left five un-narrowed
test value diagnostics; explicit value checks fixed them without suppressions.
After a tool-context refresh, the in-memory runner helper was absent and Serena
queries resolved against the accepted root rather than the authoring worktree.
The edit was inspected before continuation, no mutation was replayed, and exact
absolute-worktree file reads replaced the wrong-root queries. Tool metadata and
session caches are not repository coordinates or durable execution evidence.

The diagnostic test batch found two harness mistakes, not product regressions:
non-Git fixtures beneath the authoring worktree resolve their ancestor repository,
and immutable result data requires JSON projection before list comparison.
An inherited Git ceiling cannot isolate those fixtures because the Git adapter
intentionally removes inherited `GIT_*` variables. The corrected bounded run used
one context-managed external test root; its removal was verified. Reusing the
existing hook matrix also exposed 19 static errors from `list[object]` fixtures;
the actual `EthosResult` type now owns those annotations. Failure receipts under
`retirement-process-evidence-*` preserve the distinctions. The 269-test run binds
the unchanged product; only hook fixture annotations changed afterward and that
module was rerun. No full proof or historical lane removal occurred in this batch.

Current closeout boundaries at accepted `95b6153b` (September 10):

| Boundary | Verified evidence | Remaining obligation |
| --- | --- | --- |
| Repository proof | Source `5855feab` proof `b500cb51` and archive `95b6153b` proof `9562b7c8` independently pass 24 gates, 2797 tests with one skip and 95.19114137027037 percent combined coverage | Socket-parser changes need a new frozen proof; old failures remain failures |
| Archive and acceptance | `detached-reviewed-retirement` is officially archived under `2026-09-09-detached-reviewed-retirement`. Public candidate/accepted CAS aligned local dev, main, candidate/dev and authoring HEAD at `95b6153b`, tree `ed39ecf3` | Do not replay archive, land or accepted closeout for this object |
| Package/runtime | Immutable `2e4c7bc8` binds Alpha.5 source `95b6153b`, tree `ed39ecf3`, four hooks and OpenSpec 1.12.0. All 9681 typed inventory entries and wheel `03594114` match; installed status passes. Previous current `4bed97e3` is absent | Older retained generations still need reference-safe adjudication |
| Peer projections | Public request `91421f5f` published dev/main to both peers. Independent GitHub/GitLab readbacks equal `95b6153b`, with both signatures Verified | Publication is complete; hosted verification below is not |
| Hosted verification | GitHub dev `34416980247` passes quality, nine native jobs and source verification, but package checkout fails with HTTP2 framing errors. Main `34416980407` attempt 2 fails external links. GitLab `6370`/`6371` fail verification; job `36487` records 56 failures, 2741 passes and one skip | Fix the native socket parser through the real execution chain; investigate network failures separately without dropping links or blanket reruns |
| Physical retirement | Accepted receipts `bb4c385a`, `94562cc8`, `aff5e7d3`, `67f6f76f` retire four historical worktrees. The last removal preserves all refs, Lease rows, sibling worktrees and external Python | Three historical worktrees remain. The cumulative 53015 entries and 1534544492 logical regular-file bytes are not a claim of reclaimed APFS allocation |
| Current quality | Accepted product/test ELOC is 40000/39963. The socket fix retains product 40000 and tests 39980; parser tests pass 40 and the native uv/Nox focused execution passes 150 | Freeze, prove, archive/reprove, accept, activate, publish and observe hosted results for the socket fix |

CI root-cause evidence is recorded in the existing retirement delivery receipts.
The complete GitHub job log contains the provider's nested stdout, although
`gh run view --log-failed` omitted that long line. Parsing the raw job log shows
connection failure and timeout for the Gitleaks repository page, not a 404.
Same-host lychee and bounded curl checks reproduce network failure; GitHub API
still identifies the repository. No link exclusion, DNS/host rewrite or blind
failed-job retry is justified by these observations.

GitLab dev's exact proof records 39 failures, 2717 passes and one skip. All
reported retirement failures hit `native_process_observer_unavailable`; coverage
correctly rejects missing/stale evidence afterward. The exact cached Linux base
image lacks `lsof`, and bootstrap omits it. A small isolated image probe then
installs it: root observation succeeds, while UID 65534 fails on unreadable
`/proc/1/cwd`. Thus dependency installation alone is insufficient. Complete the
existing native-observation owner and declared CI prerequisites with a proved
Linux visibility boundary; preserve unknown/liveness rejection, do not simply
ignore permission errors or elevate the whole test suite. This is a prerequisite
for portable retirement acceptance, not another cleanup state machine.

The bounded bootstrap correction now installs `lsof` when absent. The existing
executable bootstrap regression first failed on the omitted package; after the
repair all 31 release-assets architecture tests pass. Receipts
`ci-bootstrap-lsof-red` and `ci-bootstrap-lsof-green` bind the commands and source
hashes; the context-managed test roots were removed. No source budget or
visibility policy changed. This proves dependency provisioning, not CI recovery.

`linux-single-uid-observer-probe` demonstrates a feasible unprivileged envelope:
after setup the container replaces its root process, and PID 1 runs as UID 65534
with zero effective capabilities. The unchanged observer detects the held file
and its release, while a mode-zero directory still denies access. GitLab must
apply and verify that identity boundary for the whole job, not just pytest.
The existing bootstrap now implements this boundary for the GitLab verification
entrypoint. It provisions before replacing PID 1, preserves the Runner's stdin,
and prepares only the exact checkout and declared project cache. The obsolete
pytest-only identity controls, temporary identity home, safe-directory overlay
and repeated ownership transfers are removed. Native observation is unchanged.

`ci-job-envelope-focused` records 32 architecture passes. The native execution
snapshot uses the pinned hosted image and the actual source entrypoint without
a writable host mount. `ci-job-envelope-native` proves PID 1 and the observer
share UID 65534, active/released file visibility, genuine permission denial and
writable declared caches. Its first test failure was a probe invocation error:
the omitted existing `--rootdir` produced a spawn import named `builds`. A rooted
retry instead failed while the ARM64 ShellCheck wrapper downloaded its binary.
`shellcheck-arm-build-probe` independently verifies the upstream binary hash and
successful same-version build before resuming the test invocation.
`ci-job-envelope-native-rooted-recovered` records 226 passes, removal of the
test root and container, and the exact copied-source manifest. These are native
focused results, not repository proof or hosted CI acceptance.

The GitLab CI lint API accepts the proposed configuration with no errors, but
reports the existing deprecated retry reason `stuck_or_timeout_failure`.
The native npm installation also reports two high-severity vulnerabilities;
their exact dependency paths and remediation remain to be assessed under the
existing supply-chain obligation. No automatic dependency upgrade, warning
suppression or blanket retry is justified. Current product/test ELOC is
40000/39963 at accepted `95b6153b`, with unchanged independent 40000 limits.
Source proof, archive proof, accepted runtime, publication and failure-matrix
disposal subsequently completed as recorded above; hosted CI is still failed.

The full GitLab invocation exposed a separate parser assumption not exercised
by direct-interpreter validation. `ci-job-chain-observer` reproduces the first
failure in under a minute: direct Python succeeds, while `uv` and nested
`uv`/Nox emit an identified Unix socket inode without a filesystem device.
All observed processes remain UID 65534; `lsof` exits zero without stderr. The
existing parser rejects the exact frame as `file_observation_unreadable`.
Changing identity or filtering unknown processes would address the wrong cause.

The active socket Change admits that typed socket record without inventing a
filesystem identity. Complete REG/DIR identity, malformed fields, duplicate
fields, inaccessible state and transport failures still reject. The existing
matrix first records one failure and 33 passes, then 40 passes. The first fix
exceeded the product ceiling by five lines; consolidating duplicate-field
construction and the existing field validation restores 40000 product ELOC
without reducing tests or changing limits. `socket-chain-green` verifies 150
selected tests through the real uv/Nox/pytest chain, including prior failed
retirement cases, with the container removed. Its partial coverage is not used
for acceptance; new exact-HEAD full proof remains required.

Verification errors remain distinct from product defects: the first runtime
readback incorrectly compared plain file hashes with typed mode/content hashes.
`detached-runtime-verified` independently checks the actual inventory encoding,
all entries and the wheel. No runtime mutation followed the false mismatch.
Likewise, a URL supplied directly to Lychee caused a page crawl, not a check of
that link; the original repository file and policy were then used for the
bounded recovery check. A failed-job retry after that check still failed later;
it does not justify repeated retries or relaxing link policy.

AIGW also reports an independently proved signed proposal snapshot accepted by
the installed pre-push hook, while public `publish` requires a candidate source
for proposal targets. The current ETHOS source confirms that source-role check;
the adopter's successful push is reported evidence, not locally reproduced here.
Reconcile source-object selection and diagnostics in the existing publication
owner without copying adopter history, inventing proof equivalence from tree
equality or creating a second publication path.

The failure-matrix adjudication also corrects an earlier inaccurate projection
claim: `integer_value` still parses numeric strings and returns zero for invalid
input, exactly as the historical helper did. Typed Lease validation then rejects
invalid generations. The old helper behavior was retained, not superseded by
strict parsing. Stale prose does not prove deletion or behavior change.

Historical work remains finite and classified by obligations rather than commit
count. These are observed disposition boundaries, not claims of completed
absorption:

| Historical resource | Semantic disposition and next evidence |
| --- | --- |
| `20260818-openspec-19-archive-owner` | Ten-path semantic review is complete; accepted public receipt `94562cc8` now proves physical retirement. Do not reimplement or recreate its historical supply. |
| `codex-contracts-land-test-refactor` | The shorter lifecycle topic has retired and its commits remain reachable here. Review the remaining exact-CAS, proof selection, cross-worker immutable supply reuse, worker long-tail scheduling, and cheap non-archive fixture obligations; obsolete Commitment/rebind code must not return. |
| `20260810-public-test-boundaries` | Rewritten and replaced test obligations have current-owner correspondence below; accepted public receipt `aff5e7d3` now proves physical retirement. Preserve the existing ref-intent regressions, not the obsolete Commitment fixture. |
| `20260810-coverage-source-policy-matrices` | All fifteen added definitions are adjudicated and accepted; public receipt `bb4c385a` now proves physical retirement. |
| `20260810-coverage-public-failure-matrix` | Nine original hashes, dirty deltas and all 14533 native inventory entries were reviewed; no content remained unclassified. Accepted public receipt `67f6f76f` removes the detached worktree and administration only. Postchecks prove root/registration absence and unchanged refs, Lease rows, sibling worktrees and external Python. Four-field CAS, actor readmission, public recovery and cooperative quiescence preserve useful semantics; persistent Lease content/offer binding is superseded. |
| `20260811-repository-transition-model` | Fresh CAS/Attestation, local-or-multiple-peer topology and minimal-entity intent remain valid; persistent Commitment roots and historical scope/Lease bindings are superseded. The 341 dirty items are not yet semantically adjudicated. |
| Unlinked `codex/openspec-19-archive-owner` ref | Retired through the accepted public owner; Attestation `067dd0dabfb6b6b6a5e6603c14ea84df11a026da6e8b0a0c7e0f72226b6a92bc`. Its absence does not retire the distinct dirty linked OpenSpec lane. |
| `20260908-accepted-carrier-signature-repair` | Handoff is received; seven unique commits and eighteen paths remain unaccepted. Absorb necessary signature and transaction invariants, not the command-private repair implementation by default; failed historical proof is not current acceptance. |

Execute from these obligations rather than the historical lane names:

1. Preserve accepted `95b6153b` proof, runtime, publication and four completed
   physical retirements. Do not replay successful object effects or infer hosted
   GREEN from local proof.
2. Close the native socket-identity Change through the existing process parser,
   prove the real Linux invocation, freeze and complete exact source/archive
   proof, accepted runtime, publication and hosted readback. Network failures
   remain separate evidence, not parser defects or grounds for silent retries.
3. Absorb the remaining finite sources in smallest independently provable
   semantic increments: contracts and public failure/race obligations first;
   signature-repair invariants through the current transaction owner; the large
   transition-model residue last unless a demonstrated prerequisite changes
   that order. No whole-branch merge, historical runtime revival, or one new
   lane per source is required.
4. Continue the global obligations already specified here: lifecycle and
   adopter conformance, stable supply and installed identity, quality scope and
   resource lifecycle, semantic source/docs structure and projection agreement.
   Closing the historical lanes is the first milestone, not the product terminus.

At every boundary, either discharge an acceptance/resource obligation or expose
one decisive failed invariant. If two iterations add machinery without making
the selected public outcome closer to executable, reconsider replacement or
deletion in the same owner; do not accumulate another prototype. Keep source
absorption, accepted capability, hosted delivery and physical disposal separately
evidenced. Judge the next step by the terminal capability and residue it closes,
not by a defect's proximity to the last edited file. Reuse confirmed supersession
and unchanged source evidence instead of repeatedly reopening completed review.
No unresolved item below is completed by this strategy correction.

September 9 review of the public-boundaries lane corrects a semantic-loss risk:
`ref_intent` is not retired. `git_effects` still writes, prepares, commits,
recovers and clears these short-lived transaction records. Removing a durable
Commitment or old test carrier does not prove removal of this separate protocol
dependency. The patch-boundary file retains four AST-identical public tests
(five parameterized cases); its fixture now uses official OpenSpec. The removed
nonlist-scope test only validates the superseded tracked Commitment schema.
The unexpected-path test is AST-identical, and committed-effect failure retains
its repair-required result with the current typed branch policy.

The expired-intent audit found an actual destructive race: selection sees an
expired issued record, another write changes its expiry or phase, then locked
reclamation compares only its identity and deletes the changed record. The
preservation regression failed for renewed, prepared and committed states;
unchanged expiry still passed. The existing owner now compares the complete
typed record under its existing lock. Four focused cases and the 77-test
Git-effect/admission set pass, with bound source hashes and removed test roots,
in `ref-intent-reclamation-preservation-*` and `ref-intent-reclamation-affected`.
Product ELOC is unchanged; no new lock, registry or compatibility path is added.
This proves the observation-to-lock state recheck, not arbitrary same-UID
filesystem isolation. The subsequent correspondence review below covers both
the original tests and the uncommitted rewrite rather than assuming the newer
file preserved all earlier obligations.

The subsequent real-process regression found five failures: three killed-holder
cases could not reclaim the exclusive-create lock, and both clear cases deleted
the active writer's record without acquiring coordination. Normal release passed
for the other three operations. `ref-intent-crash-red` records those failures,
not a harness error. The custom lock class and retry constants are now removed;
one existing-dependency native lock coordinates all record mutations, including
clear. Timeout retains its public error, and native capability failure prevents
mutation instead of falling back to marker ownership. One retained lock inode
per intent directory avoids accumulating locks per transaction or unlinking a
lock while contenders may still reference it. No owner registry or scavenger is
introduced. The eight-case subprocess check passed; the subsequent admission/Git
effect set passed 84 tests with byte-preservation, idempotent clear and bounded
coordination-file assertions. `ref-intent-native-capability` separately passes
the unsupported-native-lock negative boundary on Darwin. The expanded Git effect
and public-retirement set passes 108 tests in 87.60 seconds, recorded in
`ref-intent-crash-public-affected`. Receipts bind source hashes and verify owned
temporary-root removal. The first static receipt reports a broad exception
assertion in that negative test; its explicit match is corrected without changing
production behavior. A focused recheck, not another full proof, follows it.

The test's pause moved from the private store helper to the real filesystem
replace boundary after a Ruff private-access finding; product locking and writes
remain real. This increment leaves intent-directory placement unchanged: the
linked worktree resolves it beneath its Git admin directory, not directly beneath
the common root. Shared-authority placement still needs semantic adjudication.
Old and new runtime lock protocols are not mutually coordinating: activation must
exclude live old-runtime writers; this is not a claim of safe rolling upgrade.
Windows execution, archived historical residue cleanup, full proof and acceptance
remain unproved. The later user decision excludes uncooperative native-unlink
writes from the coordination guarantee. No historical lane is disposed by
these focused results.

#### Public-Boundaries Source Absorption

The bounded September 9 review covers the three dirty test files at historical
HEAD `6c523f2937f1055a2429c61c1300c6c37318b472`, including test definitions that
its uncommitted rewrite removed or narrowed. It does not claim all project
history has been recovered. `public-boundaries-historical-absorption-final.json`
binds their original and current source hashes, the current test owners and the
65 passing cases. The source bytes remain unchanged.

| Required semantic | Current owner and disposition |
| --- | --- |
| Absolute, escaping and missing patch preimages; escaping postimage; failed postimage application | Four functions in `tests/unit/adapters/admission/test_patch_admission_public_boundaries.py` are AST-identical to the historical rewritten tests; official OpenSpec replaces the old fixture carrier. Five parameterized cases pass. |
| Malformed tracked Commitment scope | Superseded by official OpenSpec and transient compilation. Do not restore the deleted carrier or its schema test. |
| Committed-effect failure requires repair; postwrite unexpected/outside paths | `test_committed_intent_gap_is_repair_required` keeps the public result with typed policy; `test_postwrite_reports_unexpected_and_outside_paths` is AST-identical. Both pass in the current failure-branches module. |
| Active intent lock is not stolen; process death permits recovery | `test_ref_intent_protects_live_owner_and_recovers_after_exit` replaces private `os.open` failure injection with eight actual holder/contender cases and preserves record bytes. |
| Missing before selection or disappearing after observation | `test_intent_reports_absence_before_write_and_after_clear` covers the first boundary; the `issued/missing` observation-matrix case covers the second, including `present=false`. |
| A valid different record replaces the selected intent | The `issued/replaced` case in `test_intent_observation_rechecks_current_storage_before_effect` uses a real public-produced record and preserves its complete bytes. A forged typed object with unchanged digest but changed operation is not a valid storage input; malformed operation is tested at the parser boundary instead. |
| Expired reclamation sees renewal or phase advancement | The same matrix retains unchanged, renewed, prepared and committed cases; prepared/committed replacements preserve the expired timestamp so phase preservation is tested independently of renewal. |
| Invalid cleanup sees a newly valid replacement | The matrix covers both claim and committed lookup, intercepting the first real filesystem read while retaining real parser, lock and cleanup. Both preserve the replacement. |
| Ambiguous claim or committed lookup | `test_ref_intent_claim_rejects_duplicate_exact_intents` covers duplicate issued and committed records; `test_committed_ref_intent_rejects_ambiguous_committed_receipts` independently covers distinct exact predecessor identities. |
| Idempotent identical writes and conflicting valid stored identity | Existing serial/concurrent tests in `tests/unit/lanes/test_ref_intent.py` retain idempotency. `test_write_preserves_valid_foreign_record_at_requested_path` replaces the historical invalid-model mock with real stored collision and unchanged bytes. |
| Invalid nonce, operation or phase; uncommitted lookup | `test_invalid_intent_rejected_and_uncommitted_lookup_ignored` covers prepared, aborted and lookup readers. Nine cases pass in `ref-intent-invalid-abort-final`; invalid phases are rejected by storage parsing, not injected beneath it. |
| Abort after commit preserves recovery; abort only removes its own transaction | Existing concurrent committed/aborted and exact prepared-abort tests in `tests/unit/lanes/test_ref_intent.py` retain both obligations and pass in the bounded set. |

Three isolated in-memory mutants demonstrate that the new tests reject using
stale selected state, deleting without an invalid-record recheck, and accepting
a foreign stored record on write. `ref-intent-historical-mutation-check*`
records them. The first mutation harness omitted future annotations and two
cases failed before pytest; those are harness failures, not caught defects.
Their corrected runs fail at the intended assertions. A separate first fixture
run used a nonexistent cwd; its corrected correspondence run passes. No current
production source was changed by this absorption or mutation check.

The existing test helper now accepts the transaction phase; repeated request
construction and duplicate identity-mismatch setup are removed without deleting
the authoritative mismatch matrix. Relative to the preceding iteration, product
ELOC is unchanged and test ELOC rises by three, within the independent ceilings.
Source absorption is complete for these changed definitions; deployment,
cross-platform proof, reviewed content disposal and ignored resource ownership
are separate obligations. This review does not authorize deleting the lane.

### Historical Necessity And Quality-Owner Review

The 2026-09-08 read-only screen at `06ea14f0` covers 3149 tracked paths. Using
first-parent content changes since `2026-08-08T00:00:00+08:00` and excluding
currently modified paths gives 1987 review candidates: 1278 official archived
OpenSpec files, 555 root historical evidence files and 154 other files. This is
an age-based candidate screen, not 1987 deletion decisions or a completed
repository-wide semantic audit. Untracked and ignored resources require their
own ownership/liveness observations. Recently modified files remain subject to
the same necessity test.

| Boundary | Observed contradiction | Required closure |
| --- | --- | --- |
| Root historical evidence | 556 tracked files, 2275604 bytes, tree `a77f77462c487a7a9b7746f3e93b4bbdad8f51ce`; the recently edited README requires preservation while denying current producers and authority | Review surviving obligations, absorb unique current meaning into its existing owner, remove obsolete bytes and their live references; retain historical retrieval through Git, not another archive |
| Evidence quality | The topology provider requires the historical root, while freshness is reduced from topology rather than exact proof bindings | Retire the root/layout obligation and duplicate scaffolding; preserve proof currentness through the actual predicate and binding owner, never by returning unconditional success |
| Docstring quality | Ruff 0.16.6 has Google convention configured but `D` unselected; a read-only `--select D` run reports 1622 diagnostics across product 241, tests 1332 and tools 49; the custom presence collector covers package boundaries and CLI commands rather than all public APIs | Activate native rules, resolve real documentation omissions and any justified role distinctions, then delete overlapping custom logic; do not hide debt with a baseline, blanket exclusions or generated filler |
| Root quality configuration | Secret scans already pass an explicit config path, contradicting the claim that Gitleaks requires root placement; Ruff and pre-commit also have explicit-path consumers | Decide placement from verified native discovery and the complete consumer chain; prove equivalent effective policy before removing the old path, with no compatibility forwarding config |
| Remaining physical structure | No complete semantic adjudication of the older 154 non-archive/non-evidence files or recent edits exists | Review by responsibility and shared invariant, not file age or count; merge duplicated owners and retain justified stable source, legal and integration files |

Root evidence disposition is locally delivered; native docstring quality and
configuration placement remain subsequent coherent owner replacements. Accepted
reviewed-content retirement closes the withdrawn prototype's public disposal
obligation without restoring its preservation design. Detached selection is
accepted and the failure-matrix worktree is retired; the newly reproduced Linux
socket parsing defect remains active. These obligations reuse this lane and
route; no second ledger is introduced.

For each replacement, first reproduce the missing or contradictory property,
then select one existing/native owner, migrate necessary meaning, delete the
superseded paths and prove the public consumers agree. Count a boundary closed
only after implementation, exact proof and accepted delivery; this review has
not activated `D`, moved root configs or retired another historical lane. The
evidence-retirement source, archive, acceptance and package readback above are
complete locally; remote publication at that object remains unproved. Git
history and selected Attestations are preserved. Each failed proof remains its
own immutable observation, not a reason to restore workspace evidence roots.

### Whole-Repository Physical Organization Review

The review includes every tracked root and the distinct physical projections:
product and test packages, tools, configuration, documentation, official
OpenSpec, schemas and rules, skills, hosted-provider files, distribution assets,
generated output, shared Git state, installed runtimes and Work Lanes. File age,
file count and path spelling select questions; none decides semantic validity.
An empty leaf has no navigation or namespace justification. A parent containing
only `__init__.py` may still own children and must be evaluated as a boundary.
A one-module leaf survives only when its public namespace, package resources or
independent responsibility justify the extra level. Conversely, flattening
several real subdomains to meet a shape target is not simplification.

The September 9 user clarification makes this a product-wide convergence
obligation, not a directory-cleanup campaign. ETHOS must provide a reusable
repository foundation: explicit intent and ownership, discoverable decisions,
cohesive implementation, executable quality, verifiable delivery and bounded
resource retirement. Consistency means the same invariant yields the same
admission and explanation across native repository shapes, not that every
repository copies ETHOS's paths or uses every optional capability. These are
requirements to realize in the existing owners, not claims that those owners
already satisfy them.

Bounded read-only comparison on September 9 sampled the following source
snapshots. The samples establish declared practices and selected physical
owners, not complete implementation quality or adopter conformance:

| Source snapshot and inspected carrier | Meaning to evaluate in the ETHOS owner | Do not import |
| --- | --- | --- |
| `di-effect` at `8a168b6b`, `docs/guides/reference/documentation-operating-model.md` and agent entrypoint | Separate subject, reader purpose, authority and lifetime; let discovery lead to one semantic owner. | Its DocOS machinery, directive projections, ADR/DEC split, generated registers or extensive README topology merely because they exist. |
| `alphasim-dmgr-fix-b3` at `513211af`, `docs/current/operations/platform/configuration-control-plane.md` | Separate deployment settings, business configuration and one-run controls; make precedence and redacted effective configuration diagnosable through one owner. | Lifecycle-shaped docs directories, embedded governance or database-specific policy. This is a distinct sample, not the `alphasim-dmgr` checkout at `57539a59` on `test/yheng-py312-np2`. |
| `aigw-cli` at `36a6a283`, `docs/decisions/decision-register.md`, transactional projection decision and agent entrypoint | Stable decision identity, control/projection boundaries, locked execution, immutable local product identity and independent peer delivery. | Client-specific concepts, credentials, a copied decision register or another publication/transaction state machine. |
| `codex-responses-proxy` at `210a108e`, decision grammar, `.config/quality/native/` and quality responsibility declarations | Separate native tool configuration from product policy; require a concrete detected risk, measured scope, remediation and review condition for each gate. | Its responsibility-map entity, transport lifecycle, thresholds or separate commit parser when ETHOS already owns the invariant. |

The comparison is a source of hypotheses, not a vote among implementations.
For each proposed absorption, identify the user outcome and invariant, compare
official/native capability with the existing owner, show what parallel behavior
will disappear, and define a counterexample the real public verifier must
reject. Reject both extremes: a mandatory cloned repository tree and a generic
metadata/registry framework that merely relocates accidental complexity.

Decision-record repair is one instance of this foundation. Current
`docs/governance/docs-registry.md` explicitly rejects numbered identity, whereas
history at `82647f3ab` already defined a numbered record grammar. The user's
lowercase correction never authorized removal of stable numbers. Reconcile the
three restored records with their historical decisions before assigning
`dr-<four-digit-sequence>-<kebab-topic>.md`; never reuse an old number for a
different ruling. Preserve context and constraints, the selected decision and
its rationale, consequences, status/date and decision provenance, verification
references and revisit conditions. Record real alternatives where the choice
needs them; do not fabricate alternatives or mandate empty sections.

[Nygard's lightweight structure](https://adr.github.io/adr-templates/) and the
[MADR template](https://adr.github.io/madr/decisions/adr-template.html) provide
the research baseline; [MADR examples](https://adr.github.io/madr/examples.html)
explicitly accommodate different levels of detail. They do not establish one
universal filename or require a second decision register. Keep specification,
decision rationale, execution progress and execution evidence in their existing
distinct owners. A substantive reversal names a successor; editorial corrections
remain traceable in Git, and decision acceptance never implies implementation.

Implement each absorbed invariant once, then verify its native configuration,
CLI, hooks, SDK, docs, skills and CI consumers where applicable. Conformance
must cover different repository sizes, languages and declared capabilities,
including local-only use; link checking or identical directory names cannot
prove it. Update the product contract, docs owner and their real validators in
the corresponding bounded successor, deleting replaced rules and projections.
This plan preserves the obligation now without expanding reviewed-content
retirement, opening another lane or changing any comparison repository.

AIGW's September 9 UTC feedback adds one unverified authored/generated admission
case: at source `67108525`, runtime `0177926d`, deleting the authored Prettier
configuration is reported as `generated_artifact_config_drift`. Its intended
replacement uses native `--no-config` to preserve parent-config isolation.
Verify classification and deletion admission in the existing artifact owner;
retain the authored/generated distinction and unique native-policy consumer.
Do not prescribe an unverified repair, bypass hooks, add a compatibility carrier
or write the adopter. This belongs to the existing projection-conformance work,
not the detached-retirement implementation.

The September 8 inventory at source `a4d2877e` covers 2592 tracked paths,
including 258 product Python paths, 197 test paths, 47 documentation paths and
17 root files. It records twenty one-module leaf packages, one init-only leaf,
and three init-only parents with children. These are review candidates, not
twenty-four deletion decisions. The ignored/local screen is shallow and does
not establish lifecycle ownership, full recursive inventory or safe disposal.
The hash-bound machine inventory is `physical-organization-inventory.json` in
the current ignored working-evidence root; this section owns its decisions and
execution obligations, not that disposable shape report.

| Boundary | Current evidence and next semantic decision |
| --- | --- |
| Python responsibilities | Review the twenty leaf packages against their callers, exports, resource lookup and reasons to change. `adapters/` and `store/state/` have real child namespaces and cannot be collapsed by direct-file count. The init-only `tests/unit/lanes/retirement/admission/` leaf is residue unless a real import or collection obligation is demonstrated. |
| Dense sibling modules | `tests/unit/cli` has 24 Python files, `adapters/repo` 17 and `tools/ci` 16. Review domain cohesion and ownership before deciding semantic subpackages; neither suffix families nor sibling count is an architectural contract. |
| Documentation | Preserve quickstart in `docs/guides` and the three necessary decision rationales; repair their lost numbered identities and content grammar as specified above. Review all 47 documents for intent/implementation agreement and misplaced policy/design/plan roles. `docs/plans/README.md` routes only to the plan already directly linked by the docs root; absorb its unique guidance and remove the redundant route. `docs/history` duplicates superseded topology rationale also discussed by the decision record; reconcile unique reasoning and Git retrieval before retiring copies. |
| Root and native configuration | Evaluate all seventeen root files through native discovery, IDE, hook, CI, package and direct-command consumers. Root placement is not justified by current existence. The configuration guide still references an absent local-state policy, demonstrating projection drift; the historical-evidence Markdown exemption is corrected in the current deletion atom. Compare tracked declarations with effective on-disk inputs and package contents before moving configuration. |
| Generated and local content | `.config/checks/pytest/build/` is an observed misplaced ignored output; use repository-rooted pytest invocations and verify the creating entrypoint, then retire exact owned residue. Source-tree bytecode, tool caches, build output, immutable supplies and Git-common state require separate producer, consumer and reclamation checks; do not copy or recursively inventory supply trees merely to make the report larger. |
| Cross-plane agreement | Trace each selected semantic move through imports, packaging, schemas, native config discovery, CLI/help, docs, rules, skills, CI and generated projections. Preserve official OpenSpec history as history, not an active state database. No relocation is complete while the old owner or its consumers remain active. |

Execute this review in the existing route: complete current evidence retirement,
dispose of already-adjudicated historical lanes, then combine structural
corrections with the corresponding unique quality/runtime/domain owners. Review
overlap before absorbing remaining historical semantics so obsolete structures
are not revived. Each bounded replacement has an exact source/destination and
consumer preflight, failing invariant or demonstrated redundancy, semantic
preservation, old-owner deletion, reference closure and current delivery proof.
Native tool configuration decisions require verified native behavior, not prose
assertions. No file-count gate, new inventory registry, duplicate design document
or repository-wide rename avalanche implements this obligation.

The September 9 follow-through distinguishes shape from actual responsibility.
The tracked-path inventory covers all fifteen root groups; it does not certify
all bodies, import edges, package resources or ignored descendants. Current
carrier reads and direct import/name searches establish these narrower findings:

| Finding | Disposition and closure boundary |
| --- | --- |
| Documentation retirement contradiction | `docs-registry.md` requires superseded documents to live in `docs/history/`, while the product contract assigns historical bytes to Git. Replace the mandatory physical-history rule in the existing docs owner; transfer the useful Git retrieval instructions before removing redundant historical copies and their stable-path requirements. Preserve the three necessary decision records. |
| Redundant test package | `tests/unit/lanes/retirement/admission/` contains only a declaration docstring. `tests/support/planning/rules.py` has a helper definition but no exact-name consumer in maintained tracked content. Confirm dynamic fixture/collection consumers before deleting both unused boundaries; do not relocate dead code. |
| Product package questions | The seventeen one-module product leaves have real responsibilities and direct callers; that proves the capability is used, not that the extra directory is necessary. Review control replacement, independent verification, dirty provenance, trust protection, topology, branch roles, proof, OpenSpec policy, skill activation and system declarations with their existing domain owners. Mixed loading/evaluation code and an obsolete `ethos-contracts` package description need owner correction, not blanket flattening. |
| Projection with no static import | `tools/projection/export_terminal_architecture.py` is selected by file path in its regression. Zero direct Python imports therefore do not authorize deletion. Inspect executable, resource and declaration consumers for every candidate. |
| Documentation role drift | `adapter-lifecycle.md` declares explanation but specifies admission policy; `evolution-campaign.md` explains learning under a superseded concept name; `local-state.md` still describes a filesystem Attestation store. Reconcile each with the current owner before renaming or moving. A diagram or Purpose heading does not establish semantic agreement. |
| Quality scope mismatch | Module-layout `semantic_paths` includes tests/tools but `package_paths` covers only product source. The empty test leaf demonstrates the resulting blind spot. Extend the existing semantic boundary where its invariant applies; do not introduce file-count quotas or another scanner. |
| Native configuration evidence | Gitleaks supports explicit `--config`, already passed by the repository runner; its alleged root-only requirement is false. Ruff auto-discovery resolves config-relative paths, whereas explicit `--config` uses the invocation directory; moving it changes the contract for IDEs and direct commands. Pytest `-c` also affects root discovery, and `--rootdir` cannot be supplied through config `addopts`. Decide each placement against every real entrypoint, not a universal relocation rule. |
| Source/declaration agreement | `.config/README.md` names absent local-state, emulator and helper surfaces; inspect every claimed native owner against tracked paths and actual callers. `system/`, `.ethos/`, `.agents/`, schemas and provider templates also need consumer-level comparison, not directory-presence checks. |

The native behavior above was checked against the official
[Ruff configuration documentation](https://docs.astral.sh/ruff/configuration/),
[Gitleaks configuration contract](https://github.com/gitleaks/gitleaks#configuration),
and [pytest root discovery](https://docs.pytest.org/en/stable/reference/customize.html).
[Diataxis](https://diataxis.fr/start-here/) supports separating reader needs;
it does not justify four mandatory directories or a README for every directory.
Retain `guides/quickstart.md`, the documentation root and irreducible decisions;
choose other locations by the content's actual policy, explanation, reference,
execution-plan or decision responsibility. Configuration moves require a
locked-version invocation test before implementation, not only upstream prose.

Review closure requires a finite disposition for every root group, every
candidate's unique meaning and consumers, exact move/deletion targets, and
cross-plane reference/behavior verification. Tracked source, ignored output,
shared Git state, installed packages, Work Lanes and provider projections must
be reported separately. Current inventory and these decisions are partial
review progress, not a completed whole-repository semantic audit. The work
remains in this plan and the existing sequence; the current deletion Change
does not acquire unrelated structure or quality implementations.

### Coverage Requirement Repair Before Acceptance

The following dated observations retain the coverage repair's evidence and
unresolved cross-cutting findings. Its implementation and acceptance instructions
are historical: `d3fc9b4c` archived the repair and current accepted `06ea14f0`
contains it. Old 38300-ELOC snapshots do not override the current independent
40000 limits. Pending Markdown, typing, resource-race and structural obligations
remain open where explicitly identified; local diagnostic results are not
whole-product or native-platform acceptance.

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

The September 7 failure-matrix comparison initially left public Lease
storage-error and mixed-state projection correspondences open; the accepted
tests described below cover them. September 9 revalidation in the same
`historical-failure-matrix-audit.json` confirms all nine source hashes and
compares 38 changed/added or untracked test definitions. Seven paths have current
correspondence; two Lease/lifecycle files still require coordination adjudication.
The earlier selected current owners passed 104 tests with
unchanged hashes and no remaining temporary root. This is not full proof or
retirement authorization.

The public ref-failure sequence is now verified without restoring the historical
compensation state machine. The existing real superseded-retirement test covers
linked and already-unbound entry, success, failure before ref deletion, and an
error returned after actual ref deletion. It checks unchanged accepted and Lease
coordinates, exact completed/remaining effects, original-receipt recovery, and
two recoveries without replaying completed removal, ref or Lease effects.
`historical-retirement-public-sequence-corrected` records six passes; production
source was unchanged. The preceding two failures were a fixture-output whitespace
expectation, not product RED. A separate process-local mutant reintroduced the
deleted ref into remaining effects; the new regression rejected that replay.
Its failing receipt is `historical-retirement-public-sequence-replay-mutant`.
All nine historical input hashes still match. These results close this specific
failure-sequence evidence gap, not verified participant quiescence or authority
to delete historical content under the later confirmed coordination boundary.

An isolated process probe confirms the unique runner captures stdout and stderr;
the retired `capture_output=False` option needs no replacement. Invalid holder
input is rejected by the typed request. A malformed Lease schema raises inside
the adapter, but the actual public CLI returns a structured block with observed
and expected columns and an exact hook-install recovery command; it leaves the
database unchanged. Do not misclassify an internal exception as missing public
diagnostics, or claim migration succeeded when only its diagnostic was tested.

Separate takeover probes write new content immediately before or after the
holder CAS. Both retain those bytes and transfer the holder to generation 2.
The old requirement to roll back a Lease bound to HEAD/tree/payload is not the
current four-coordinate model; content loss was not observed. However, the
current authorization's `quiesced` or `source_lost` assertion alone does not
stop a writer. The user-confirmed boundary now requires actual writers to stop
and honor coordination; it does not require fencing uncooperative same-UID
processes. Finish the finite historical correspondence under that boundary,
without restoring persistent content binding. All historical inputs remain
untouched.

The next finite coordination review exposed an actual authorization bypass:
after a valid takeover, replaying the same request as the old holder returned
`pass` and persisted another native effect Attestation. Initial application
checked the actor, but the recovered path replaced those gaps with authorization
checks that omitted it. `historical-lease-recovery-actor-red` reproduces this
against real temporary Git/SQLite state. Actor equality now belongs to the shared
authorization owner used by both initial and recovered invocation; the four-line
check is moved, not duplicated. No Lease schema, content binding or new recovery
state is introduced. Old-holder and empty-actor regressions pass; their record
count and subsequent exact revocation also protect the no-additional-effect and
unchanged-Lease postconditions. `historical-lease-recovery-actor-affected` binds
56 passing Lease and CLI tests, unchanged source hashes and removed test roots.

This closes recovered-invocation admission, not writer exclusion. The confirmed
cooperative boundary requires stopping actual writers rather than inferring it
from `source_state`; no filesystem-fencing subsystem follows. The two historical
Lease/lifecycle files still require final bounded correspondence, not a new
isolation guarantee. Their old persisted
HEAD/tree/payload and offer identities remain superseded; the current actor,
generation, expiry, accepted authorization and storage-failure obligations stay
in their existing owners. All nine historical source hashes are unchanged.
The authoritative OpenSpec projection still names handoff-offer/accept and a
workflow-declaration owner although current code uses transfer and takeover;
that projection discrepancy remains a separate unclosed semantic obligation,
not a reason to restore the old state machine inside this retirement Change.

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

Coverage is now accepted; this dated audit does not justify inserting supply
churn into the active retirement Change. Execute the bounded supply successor
after the immediately qualified lane disposals; do not create another lane or
simultaneous active Change. First close
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

### Easiest-First Retained History Retirement — 2026-09-08

The retained-topic capability was accepted at `53a99db42` and remains in
current `06ea14f0`. The clean lifecycle topic at
`994b301f73604780202d25a8ef52d239c24ec4fe` is wholly reachable through the
contracts topic at `c4ec2ebbc05beb11df15b1b8528c182402c0effe`: their exact
left/right unique commit counts were `1/0`. Public retirement removed the shorter
topic's worktree, ref and Lease. This is one of seven historical worktrees
retired, not seven semantic absorptions. Its remaining meaning still belongs
to the contracts topic's pending review.

The existing immutable operation binds the exact retained ref/OID, source,
accepted coordinates and current authority; no preservation store or historical
configuration is restored. Regression evidence covers installed hooks, retained
assertions, holder rules, invalid retention, stale coordinates and pre-CAS races.
The archive-HEAD proof records 25 passing gates in Attestation
`912c40f0b72794ba45b149c79a55d1b1cc5d96ee26ef3b0fab31e4e2d0b51ec7`.
Do not replay that completed delivery sequence.

The September 8 budget decision sets independent 40000-ELOC product/test
ceilings; the project total is observational, not a 90000-ELOC blocker.
The latest user guidance authorizes independent ceilings of up to 45000 ELOC
for product and tests when a bounded semantic-consolidation review finds that
further reduction would sacrifice necessary behavior, test evidence, clarity
or delivery efficiency. This is conditional headroom, not a growth target or
permission to disguise source, remove obligations or compress formatting.
No proof of a theoretical minimum is required. The current measured overlay
has 39999 product and 39999 test ELOC, so the executable ceilings remain 40000
for now. When this condition is met, update the sole numeric policy owner and
its checked projections before acceptance; do not repeatedly seek the same
authorization or continue mechanical line trimming. Coverage remains at least
95 percent, and the two source budgets cannot compensate for each other.
Generated Mermaid output is excluded from maintained source while its C4 input
remains counted. These measurement rules do not prove quality effectiveness.
The cwd-sensitive historical gate-registry problem remains deferred, not a
prerequisite for every remaining source or a reason to revive old runtimes.

### Quality-System Effectiveness — 2026-09-08

The user requires repository-wide quality, not only budget compliance. Preserve
the existing source-budget decision's maintenance-cost rationale; replace its
mandatory aggregate ceiling rather than inventing a new score, metric runtime,
or report registry. Product and test size are independent hard constraints;
other category totals expose growth but do not substitute for semantic review.
Generated and archived records remain visible separately; active intent, docs,
configuration, and generators remain maintained source. The 95-percent combined
coverage floor is unchanged and cannot be paid for with source reduction.

Current evidence identifies a concrete assurance gap: the type adapter translates
configured package `.` into `src`, so its successful repository configuration
does not prove tests or tools are type-correct. Explicit changed-file checking
found 92 diagnostics in test/report contracts and fixtures; this batch resolves
them without suppressions, widening to `Any`, or a second runtime model. The
existing report's wire shape is described with TypedDict and fixture assertions
narrow actual values. Full test/tool typing is still unproved, not implicitly
covered by this repair.

After the current retirement result, audit quality owners by the failure each
must detect, exact source/fixture scope, admission phase, evidence binding,
runtime cost, and public failure action. Prioritize false-green scope and
identity gaps, then decisive independent boundary assertions, native-tool
reuse, duplicate gate removal, and resource/crash closure. Reuse official tool
documentation and existing decision rationale before introducing a metric.
Verify representative faults are rejected by their real gates; a counter, test
count, formatter result, or passing package smoke alone cannot establish this.
Correct scope declarations and consumers together, measure the affected baseline,
and close bounded owners without pausing already-safe lane retirement for an
unlimited audit. The current Change does not redesign the whole quality system.

#### Whole-System Quality Closure — 2026-09-10

Quality is the chain from a product requirement and its risk, through one
check owner and exact source/fixture scope, to a counterexample, enforced
verdict, actionable repair and version-bound evidence. Counts of tools, rules,
gates or passing tests are not a substitute for that chain. The scope includes
product, tests, tools, declarations, documentation, official intent, schemas,
packages, installed runtimes, native platforms, provider projections and the
resources created while checking them. This table records observed gaps and
required closure; it does not declare those properties delivered.

| Quality responsibility | Existing owner and observed gap | Required completion evidence |
| --- | --- | --- |
| Intent and semantic preservation | Product contract, official quality spec and this plan; older tool findings were not consistently carried into execution | Every distinct obligation is accepted, superseded with reason, deferred with a trigger, or rejected; code/spec/docs/skills agree and no useful capability disappears during deletion |
| Selection and execution | Gate declaration/compiler/runner versus private local-CI session lists; typing/budget and security/carrier checks differ between entrypoints | One declared graph and runner; equal requested planes have equal required closure; duplicate aggregate execution and private scheduling are removed |
| Dependency and failure admission | Shared waves previously executed delivery after failed or unknown coverage | Independent RED cases for both outcomes, unexecuted dependent results with exact causes, no success receipt for an incomplete closure; preserve independent diagnostics |
| Python correctness and documentation | Ruff and Ty remain sole native owners; `D` is absent and configured Ty `.` was narrowed to `src` | Native-rule changes reject representative faults across product/tests/tools; repair actual signatures and non-obvious contracts, retire overlapping custom docstring logic, preserve useful role distinctions without blanket exclusions |
| Structure and maintainability | Module-layout, import-linter and source budgets; duplicate module identity parsing, empty test leaves, test-scope gaps and shallow/parallel owners remain | Resolve ownership using callers, dynamic registration, resources and independent change reasons; verify imports and public behavior after deleting incumbents, not file-count-driven moves |
| Behavioral assurance | pytest, Hypothesis, combined coverage and selected mutation testing | At least 95 percent combined statement/branch coverage without exclusions or dilution, risk-selected boundary/state-machine/concurrency counterexamples and scoped mutation evidence, not copied implementation assertions |
| Carrier and projection integrity | Native format/schema/link owners and generated-asset checks; full proof did not include every local-CI carrier check | One effective configuration per property, all maintained admitted carriers in scope, cross-plane references and generated projections checked, archived/generated quantities separately reported |
| Dependency and security assurance | deptry, locked supplies, uv audit and Gitleaks; native owners exist but security checks are not in the proof registry | Inventory/source/lock/runtime agreement, dev-tool reachability, secrets and vulnerable/adverse dependency counterexamples; online freshness distinguished from offline correctness and tool provisioning |
| Package and provenance | Build/install owners and Syft; SPDX version recognition alone is not complete conformance | Exact wheel/npm contents, reproducibility, install/upgrade/rollback/uninstall, standard SBOM conformance and license coverage, provenance, signatures and publication each proved separately |
| Runtime and resource safety | Temporary/supply/runtime owners and native process observation | Normal/crash/SIGKILL convergence, live-root protection, read-only-tree deletion, shared supply, bounded 24/48-hour item/byte/inode/latency/indexing cost; no artificial TTL increase or manual broad cleanup |
| Delivery and platform assurance | Native macOS/Linux/Windows matrix, Git/Forge publication and installed readback | Exact local object and independent remote refs/signatures, actual hosted jobs and assets, installed source/tree/digest; network failure, pending projection and real divergence remain distinct |
| Gate effectiveness and economics | Existing quality owners, not a new quality platform | Each mandatory check detects its claimed real fault, fails closed on malformed/missing/stale evidence, preserves stderr/cwd/binary/actor, runs within bounded resources and has one repair path |

The `quality-assurance-owner-closure` Change was accepted at `c9aad4a80` after
both source and archived-source full proofs passed all 35 selected gates.
Installed-runtime inventory and both independent remote dev/main refs were
read back at that object; hosted CI completion remained unproved. This repairs
selection and prerequisite-result enforcement, not every row at once. Independent
product/test ceilings remain 40000 and combined coverage at least 95 percent.
Subsequent replacements remain globally required: native Ruff/Ty
scope, metric correctness, semantic structure/docs/configuration, security and
supply conformance, resource lifecycle and provider/adopter closure. Independent
historical lane absorption is not postponed until the entire audit finishes.

##### Research Intake And Quality Effectiveness

The user-authorized September 10 research input is
`ETHOS-research-2026-09-10.md`, verified SHA-256
`3a68c70f3b545c1535a8581a0b5dbd2fdc1e07191a51c5e5e00d0d8196f08c3c`.
Its `3e1687cd` observations are historical, not current accepted coordinates.
External source inspection is evidence of the inspected implementation, not a
common-workload result, independent identity guarantee or comparative ranking.
Existing product meaning and the current public runtime remain authoritative.

| Obligation and disposition | Existing owner and bounded next verification |
| --- | --- |
| Accept reliable human/Agent continuation; correct the passive reader loop | Accepted `6baee9a0` removes the workspace fallback and reuses exact closeout derivation; both exact prearchive and archived full proofs passed 35 gates, and installed detailed status ends with `done`. Real idle, foreign-lane and pending-candidate cases must distinguish done, detail expansion and an actual next operation; blocking causes remain visible. Reader done is not global goal completion. |
| Accept candidate/verification-attempt separation and bounded reuse from COMET/SpecD | Existing proof bindings and Fact providers must invalidate reused observations on relevant source, policy, environment, toolchain or external-fact changes. Keep a valid candidate when only verifier availability changes; distinguish Lease expiry, owner liveness and child liveness. Strong evidence belongs at the actual trust boundary, not in duplicate snapshots or trajectories. |
| Accept trusted-prestate policy continuity from RepoKernel/gittuf; strength remains unproved | The policy/compiler and independent-verification owner must reject candidate self-downgrade under trusted prior policy. Identity, permission, quality and freshness are independent conjunctions. The currently disabled profile path is not evidence of default independent enforcement. Exercise control-policy replacement, rollback and absent verifier; ordinary changes need not acquire a universal heavyweight verifier. |
| Accept official OpenSpec archive-fidelity replay before upgrade | Official release/API observations found 1.13.0, published September 10 at 05:10 +0800. Replay repeated delta sections, CommonMark list markers, fenced blank lines, wrapped scenarios, skip_specs and archived proof identity through the official CLI. Then update existing supply/lock/package/runtime owners together. Do not implement a second Markdown parser. |
| Accept stable capability seams and source checks, not another framework lifecycle | Fact/Context providers and existing Skills may supply domain capability. Spec Kit extension and resume checks are candidates for bounded adaptation. Keep one merge/archive/publish effect owner, no persistent graph or framework state beside the repository authority. |
| Accept standard interoperability only when a consumer needs it | Materials, products, identity and provenance from in-toto/DSSE/SLSA inform existing evidence boundaries. A standard adapter needs a demonstrated cross-system consumer; Source Track and build provenance must not become a second policy authority. Signatures or HMACs alone prove neither independent execution nor current permission. |
| Require greenfield and brownfield vertical conformance, not bootstrap claims | Exercise formation/adoption, first accepted change, Agent handoff, cooperation/competition/drop, interruption, partial publication and exit. Reuse domain Skills/templates; preserve brownfield layout and do not retroactively certify its history. Two-file bootstrap, compensating exceptions, Git ref CAS and cross-Forge effects have distinct guarantees; uncertain results remain unknown. |
| Preserve exact foreign/dirty-lane ownership and useful results | Three historical lanes still require semantic absorption and exact retirement. Verify relationships, receive authorized handoff, conserve unique content and prove recoverability before deletion; visibility is not ownership. Do not revive obsolete persistent Commitment or full-semantic Lease carriers. |

The cross-domain supplement `ETHOS-cross-domain-research-2026-09-10.md` was
read in full and verified as SHA-256
`3142f47dabecbacf6d25009d1f21843b5448e7d7870eda27aeda5239f2422e3e`.
Its third-party claims are fixed-source research, not executed common workloads.
It corrects the product scope: the small trust kernel serves the complete path
from problem/value and research through interpretation, accepted intent,
capabilities, execution and delivery to actual use, learning and exit.
The product contract owns that meaning; this existing plan owns the sequence.

| Stage and disposition | Existing owner, concrete obligation and exit evidence |
| --- | --- |
| P0 accepted; hosted observation remains separate | `status-observation-completion` reached accepted `6baee9a0`, exact immutable runtime and both peer `dev/main` refs. The installed runtime's 9681-entry inventory matched. New hosted jobs were queued, not proven green. Do not reimplement the accepted quality executor or reader fix. |
| P1 intent fidelity, now active | `intent-source-fidelity` replaces the lossy context extractor, preserves exact sources and identifies structural interpretation as unassessed. An official-valid `*` list previously erased non-goals/questions; a fenced pseudo-heading polluted them. Source-preservation tests are the first boundary, not completion of the all-drop trace. FRET/KAOS examples and BAML omission counterexamples inform source accounting without introducing a second intent store. |
| P2 acceptance and capability compilation | Existing OpenSpec compiler, Facts, Plan and capability seams must bind source scope, accepted meanings, assumptions and distinguishing proof obligations. Same normalized inputs produce the same result. Verify removal/negative requirements, exceptions, skip_specs and unresolved conflicts; a source hash or valid structure is not sufficient behavioral proof. |
| P3 collaboration and effects | Existing effect adapters retain exact generation/authorization fences, fresh UOW reads and retry boundaries. Separate attempt, effect, durable result and ACK; use real kill, lost ACK and concurrent-change traces. Replaying history never grants current permission. Quint-style minimal traces and Temporal/Restate/DBOS/AWS boundary cases are methods, not a new runtime. |
| P4 formation and progressive adoption | Existing adoption and specialist scaffold capabilities must complete real greenfield and brownfield paths, preserving domain layout and customization. Template evolution compares old template, customization and new template; generators propose candidates and conflicts remain visible. Verify upgrade, withdrawal, handoff and uninstall without retrospectively certifying old history. |
| P5 measured evidence reuse | Existing proof and observation owners separate candidate iteration, execution and verifier judgment. Cold, warm and cache-cleared verdicts must agree; all relevant inputs invalidate reuse and actual computation must fall. COMET/Inspect rescoring and Bazel/Pants/DICE/Nix input-closure ideas apply only after measurement; advance this stage when throughput blocks progress. Hard constraints cannot be offset by DSPy/GEPA-style scores. |
| P6 actual-use feedback | One required outcome observer binds deployed identity, baseline, fixed window and environment. Distinguish unavailable observation from unmet goal. A counterexample can invalidate current applicability without changing historical evidence, and motivates a source-grounded Change without granting mutation authority or lowering standards. Argo/Keptn/assurance methods remain thin integrations. |
| P7 replaceable ecosystem | Capability input/output, permission, identity, version and failure contracts constrain P1 onward. Freeze public SDK/CLI/Skills/thin adapters only after independent implementations pass a common workload. Reuse existing registration/distribution; no empty marketplace, persistent graph or claimed cross-repository transaction without an actual shared atomic boundary. |

The common acceptance trace starts from the user's explicit allowance for zero
winners and preservation of useful results. Reject mandatory-winner, drop-means-
worthless and nonintegration-means-destruction interpretations. Then exercise
multi-contribution cooperation, one/zero-winner competition, negative findings,
stale-proof refusal, interrupted recovery and controlled retirement. Invalidate
an environmental assumption without rewriting history; a replacement Agent must
continue from repository sources without asking the user to repeat all history.
This full trace and independent capability substitution remain unproved.

For the declared workload scope, require every relevant source constraint to
have an explicit disposition, all critical counterexamples to distinguish wrong
behavior, reachable legal success and no duplicated destructive effects or lost
results in tested fault windows. Unknown never becomes green. Measure false
admission/blockage, repeated questions, handoff/recovery time, resources and
maintenance touchpoints; source maps, graphs and tables are projections rather
than additional authority. Global quality scope, latest stable supply and
historical lane absorption remain obligations alongside this sequence.

An unrestricted Ty read at accepted `6baee9a0` reported 487 diagnostics; the
current intent-source overlay reported 484 before further fixture replacement.
The current type gate only selects package `src`, so a passing gate is not
whole-repository typing evidence. Product source and the changed test files
pass their targeted checks. Native quality closure must extend meaningful test
and tool scope and retire duplicate fixtures rather than suppress these findings
or claim they were introduced by the current Change. Exact logs remain in the
existing owner-scoped evidence directory.

Quality effectiveness is a four-part obligation: the required property has an
executable rule; the rule covers every meaningful maintained carrier; an
independently chosen wrong mechanism causes a distinguishable failing
observation; and all relevant entrypoints enforce that result. A successful
check only establishes its observed scope. Broad green, task checkboxes, source
size and installed-tool counts cannot substitute for these obligations.
Measure false admission, false blockage, repeated side effects, result
conservation, manual continuation cost, latency/resources and maintenance
touchpoints using the same workloads before claiming improvement.

The tracked Python audit at `b49edd95` found 39 of 259 product modules,
124 of 186 test modules and 6 of 30 tool modules without a module docstring;
the root Nox module is documented. All 476 tracked Python files were inspected.
The existing docstring owner nevertheless returned `pass`, reporting 98 of 98
selected symbols documented. Its denominator contains package boundaries and
CLI functions under product source, not all maintained modules. The 169 missing
module descriptions therefore coexist with its claimed 100 percent result.

Executable stdin counterexamples confirmed that configured Ruff accepts missing
module documentation in product, package, test and tool paths. Explicit
`D100/D104` selection rejects those public carriers but still accepts a private
module path. Enabling `D` alone does not prove every-module coverage. Native
rules own supported presence/style semantics; any retained check must prove a
specific unsupported obligation rather than duplicate their parser or inventory.
The next native-quality replacement must enforce meaningful module
responsibility/boundary documentation across maintained Python, retain necessary
public API contracts, and retire overlapping collectors. Empty namespace shells
require necessity review, not filler documentation. Counterexamples must include missing ordinary module,
package, test and tool documentation plus ineffective rule/scope selection;
do not hide omissions in exclusions or mechanically generated prose.

Execution remains bounded: P0 is accepted; advance P1 intent fidelity without
indefinitely deferring semantics behind native quality work. Quality effectiveness,
official supply fidelity and easiest-first historical lane retirement remain required. Trusted-policy counterexamples precede any claim of
default independent protection. Full adoption workloads close the broader product
mission; they are not silently added to this reader Change.

##### Hook And Extension Boundaries

The September 10 user feedback connects hook reach, plugin composition,
observability, verification latency and excessive handwritten mechanisms. Treat
these as one boundary-design review, not permission to add independent policy,
workflow, intent or event stores. The following directions are proposed;
implemented conformance and workload measurements decide their adoption.

| Boundary | Intended responsibility and positive admission | Excluded inference and verification |
| --- | --- | --- |
| Host tool dispatch | When the host supports it, pass structured tool intent, actor, exact root and patch or ref scope to the existing admission owner before a managed mutation. | A shell command string is not a complete effect description. Nested scripts, aliases, child processes and direct filesystem writes require execution-boundary controls; a hook is not a sandbox. Recheck current facts at the effect. |
| Native Git events | Keep commit message, commit and push admission at their native events; use reference transactions for exact ref changes. Post-checkout, post-merge and post-rewrite may invalidate affected derived observations and report continuity gaps. | Post-event failure does not undo the completed mutation. Git has no universal before/after command hook. Status may refresh the index, so post-index-change cannot establish a semantic content change. Background observation should avoid optional index writes. |
| Official OpenSpec operations | Reuse the official command for generation, validation and archive. At a managed write boundary, compile the exact accepted artifacts, execute once and read back actual outputs and identity. | Installed OpenSpec internal Commander hooks are not demonstrated public plugin hooks. Do not monkeypatch its internals, fork its Markdown parser or claim every raw invocation is intercepted. |
| Evidence and performance | Guards perform bounded relevant checks; observers report timing, outcome and exact evidence references. Changed input identity invalidates only evidence whose full dependency closure changed. | Trace events do not mint Attestations or grant authority. Lost hook notifications require fresh reconciliation, not stale-cache trust. Check duration and output limits; never run full proof on every read or small edit. |
| Continuation and retirement | Session or task boundaries can report unresolved effects, useful unintegrated work, running children and exact next actions through supported host events. Cleanup owns only exact admitted resources. | Session end does not prove an owner exited. Missing or failed callbacks cannot authorize deleting a lane, releasing a live Lease, replaying a mutation or silently claiming completion. |
| Extension composition | Versioned typed inputs and outputs, declared permissions and trust provenance feed one deterministic admission result. Independent observers may run in parallel; side effects have one owner. | Do not depend on hook registration order or assume one denying hook prevents another hook from starting. Pure guards cannot perform mutation while awaiting aggregate approval. Optional telemetry failure and unavailable mandatory admission have different outcomes. |

Use event-driven invalidation, demand-driven recomputation and fresh effect-time
admission together. A hook notification is a hint to invalidate an affected
projection, not a completeness guarantee or permission to reuse stale evidence.
At first observation after missed events, reconcile authoritative inputs.
Context hooks may select relevant accepted intent, assumptions and capabilities;
they do not accept interpretations or activate unrelated skills. Expensive
checks are deduplicated by complete input identity and run outside the tool's
synchronous critical path; mutation admission remains fresh.

The installed Git 2.55.0 documentation and a successful `git hook list
--show-scope pre-commit` probe expose native config-based hook composition.
Evaluate that substrate before writing another hook dispatcher, with explicit
supported-version and trust/config-precedence checks. Trace2 is the native
observation candidate for status and other Git command timings: a bounded
`git --no-optional-locks status --porcelain=v1` probe emitted command, timing and
exit events without changing hook configuration. This single probe establishes
availability, not performance overhead, full interception or secure auditing.
No native pre-status event is inferred and no new hook is installed.

Hook capability discovery must report supported, configured, trusted and armed
separately. Require measured latency, bounded recursion, output redaction,
collision handling, loss recovery and uninstall behavior. Test stale coordinates,
wrong roots, nested mutation, concurrent handlers, duplicate delivery, timeouts,
crashes and valid non-blocked paths. The current installed four Git hooks do not
prove host-wide tool interception. Host documentation is not evidence that this
Desktop session has a particular event enabled.

Research anchors: Git's official githooks and git-status manuals define the
native event and optional-index-write boundaries; OpenAI's official Hooks guide
states that matching handlers may run concurrently and non-managed definitions
require trust review. Their behavior constrains thin adapters, not repository
meaning. No new hook has been installed by this review.

##### Unified Mechanism Review And Verification Throughput

The next architecture decisions must separate constraint compilation, pure
policy decisions, legal state transitions, effect execution and evidence
reuse. A framework is useful only when it replaces an existing mechanism and
preserves these boundaries. CUE may compose and validate configuration; CEL may
evaluate pure guards; a state-machine library may describe legal transitions.
None alone supplies fresh authorization, Git or SQLite CAS, crash recovery or
complete semantic intent. Keep Git facts and bounded Lease coordination rather
than introduce another persisted workflow truth.

Observed at source `9a774f98`: CEL is already installed and used by artifact
path policy. Its facts, policy and rule variables are dynamically typed. A
misspelled field and a non-boolean expression passed expression compilation in
small probes but failed evaluation. Evaluate stronger declaration typing and
bounded cost before expanding its authority; runtime rejection is not compile-
time validation. CUE is declared optional and was not found on the effective
PATH. Its adoption must replace demonstrated configuration/schema repetition,
not add a second manually synchronized model. These are bounded observations,
not a whole-repository framework audit.

The gate runner currently executes barrier-separated waves; the test owner
uses module-scoped scheduling. Recent local full proofs took about 17--19
minutes; the latest archived run took 1158.07 seconds, with 930.563 seconds of
testing and 887.485 seconds in one module. GitHub main source verification for
`6baee9a0` completed successfully in about 75 minutes. Both hosted templates
uploaded proof but omitted test-owned JUnit and coverage artifacts. These
observations justify advancing measured throughput work without reducing proof
obligations. They do not establish a measured speedup or complete root cause.

Immediate `verification-feedback` scope is native work stealing and visible
source-bound reports, with failure-preserving transport. Next evaluate ready-
node scheduling against real resource conflicts, reduce heavyweight fixture
setup at the semantic boundary, and derive reusable execution identities from
all relevant source, policy, environment, toolchain and external inputs. Cached
execution evidence may support a newly evaluated proof only when its complete
inputs and trust remain applicable; final authorization is always fresh.
Archive and ref-only changes must not force unrelated computation once this
identity model is proved. Cold, warm and cache-cleared verdicts must agree.

Python remains `>=3.12`. PEP 695 generics and stronger typed capability seams
are candidates for reducing ambiguity, not syntax-count goals. A live probe
showed that replacing an Annotated alias with a named `type` alias preserved
its value dump but changed Pydantic's JSON Schema shape. Schema and digest
compatibility must therefore be tested; modern syntax is not automatically a
behavior-neutral rewrite. Measure deleted duplication, distinguishing failures,
actual latency and recovery cost rather than counting frameworks or rules.

##### Executable Semantics Research — Accepted Increment

The user confirmed the queued research plan associated with feedback
`01a08b4f-5ef5-7820-bc1b-f12fac269744`. The existing report
`ETHOS-semantics-design-research-2026-09-10.md` was hash-verified as
`933491d6b128a02e1e271dafbb32366297e2b3814be10665c61dab98393d3eb7`.
Its external-source and mathematical claims remain research with the stated
limits, not implemented capabilities or a second product contract.

Current evidence supersedes the report's coordinates: local accepted source is
`9a774f9852d117909942d89218ed66b32687aa89`, with matching installed runtime
`5e22f8da2362cb2ee477762facfd41c10862ce508bf87065c840dc935fe154c2`.
The idle lane-status loop is already fixed. The active `verification-feedback`
Change remains bounded to scheduling and hosted report visibility. Its current
86 affected tests pass; full proof, timing comparison and remote visibility are
not yet demonstrated for that overlay. Do not restart completed work or label
queued semantic changes fixed.

| Disposition | Existing owner, evidence and reason |
| --- | --- |
| Accept binding and program-point defects | `repository/policy/references/python_syntax.py` and `observation.py` own the observation, with `closure.py` consuming it. A source-bound public `prove --host --execute --gate repository-audit` run reproduced module/member alias omission, local shadow false detection, and cross-scope/program-point environment misattribution. Repair the unique owner, not callers with spelling lists. |
| Adjust the claimed impact | In both alias cases the public result's semantic-closure component said pass/evaluated with no unknowns; direct control and local shadow both reported an executable orphan. Other audit obligations kept the outer result blocked. This proves incorrect public subjudgment, not a complete governor bypass or actual external command execution. |
| Evaluate LibCST, do not preselect it | Qualified names and scope metadata are a candidate replacement for binding heuristics. Require executable tests for supported syntax, conditional bindings, reassignment, reflection, cold/hot cost and immutable package closure. Name candidates do not establish values, callee effects or complete data flow. No dependency was added. |
| Accept property-scoped uncertainty | Distinguish syntax availability, resolved identity, possible values/effects and unsupported analysis. An empty extracted set is not a proved absence. Carry unknown provenance through the relevant obligation; do not freeze unrelated operations or turn uncertain discovery into permission. |
| Accept minimal model promotion when necessary | Existing OpenSpec, transient Commitment/Facts/TransitionPlan and persistent Attestation remain the owners. Add only distinctions required by falsifiable cases and migrate all consumers; no persistent semantic task graph, competing intent database or second lifecycle. |
| Accept resource and composition reasoning | Shared refs, SQLite, caches, processes and external resources determine interference, not different worktree paths. Validate the actual selected contribution set under a fresh baseline; pairwise success does not prove joint consistency. Lease remains coordination, not a semantic database. |
| Accept preservation and refinement obligations | Deleting an owner must preserve or migrate useful consumers and evidence. Specify which meaning survives carrier/adapter transformations and which approximation remains. Hash equality, graph edges, vector similarity and schema validity cannot substitute for behavioral acceptance. |
| Accept safety and progress together | The reference model must expose legal success, interruption, retry, unknown results and declared environment/fairness assumptions. Counterexamples must cover both unsafe admission and permanent false blocking. Use finite models and trace conformance where relevant. |
| Decline wholesale platform adoption | DPO, MLIR effects, abstract interpretation, Institutions, e-graphs and temporal models provide design/test methods. No current case justifies deploying the listed graph, ontology, compiler or proof-assistant stacks as a new product platform. |
| Accept the full product chain | Research, interpretation, accepted intent, capability composition, execution, delivery, actual outcomes and exit remain required. Code semantics supports this chain; it does not replace greenfield/brownfield adoption, Skills, exploration, handoff or learning. |

The bounded scheduling comparison ran the same nine land-readiness cases with
8 workers and unchanged measured inputs. Scope scheduling took 238.722 seconds;
work stealing took 82.504 seconds. Test identities, outcomes, per-line execution
and branch observations matched. The elapsed ratio was 0.3456 for this selected
workload only; one sequential comparison is not a whole-suite or independently
controlled benchmark. Both runs kept isolated coverage, not current proof data.
The comparison receipt is `verification-feedback-scheduling/comparison.json`.

The exact public reproduction is retained in the existing ignored evidence
location as `semantic-public-gate-reproduction.json`, alongside
`verification-feedback-affected.log`. It contains six immutable-runtime CLI
invocations against isolated source snapshots, input hashes, outer and inner
verdicts and cleanup confirmation. Sample programs were parsed, never executed;
all temporary repositories were removed. The outer audit's unrelated failures
remain recorded rather than suppressed to manufacture a bypass.

After the current bounded Change closes, the next reference-observation Change
must start from these public counterexamples. Name-preserving import rewrites
must preserve the declared observation, while same spelling with different
binding must not inherit effects. Program-point and conditional-value tests
must distinguish known values, possible values and unsupported behavior.
Declare observational equivalence explicitly: traceback names, reflection and
exports are not assumed unobservable. Delete replaced heuristic paths, test
consumer/public propagation and require the current proof before acceptance.

The full-chain acceptance case remains required across the existing P1--P7
sequence; it is not added to the small report-transport implementation:

1. Read the original permission to cooperate, compete, explore and drop all.
   Reject the stronger interpretation that a winner is mandatory. Accepted
   meaning and non-goals are persisted only in official OpenSpec.
2. Compile explicit subjects, assumptions, acceptance conditions, capability
   requirements and proof obligations; unresolved meaning is not silently lost.
3. Execute cooperative multi-contribution, explicitly single-winner zero/one
   selection and exploration with valuable negative results across worktrees.
4. Validate the selected combination, including a case where each pair of
   constraints is satisfiable but the whole set is not. Observe shared-resource
   conflicts and reevaluate on every target-baseline or policy change.
5. Apply the exact CAS once; inject stale coordinates, process kill and lost
   acknowledgement. Distinguish failure from unknown outcome and recover from
   actual state without duplicate destructive effects.
6. Retain useful code, reasoning and experiment outcomes before controlled
   retirement. All-drop is a valid no-integration result, not data destruction.
7. Switch Agent using accepted intent, current facts and result evidence;
   continue without requiring the user to restate the full history.
8. Repeat one complete greenfield and one brownfield adoption, retaining domain
   customization. Bind real-use observations to deployed identity, baseline,
   environment and observation window; feed counterexamples back to the source
   goal or assumption without rewriting historical evidence.

P0 closes facts/feedback/current quality first; P1 intent semantics and extension
contracts, P2 executable compilation, P3 collaboration/recovery, P4 both adopter
paths, P5 measured reuse and risk-based verification, P6 outcome feedback and
P7 independent ecosystem conformance retain their existing order. P5 may move
ahead where measured throughput blocks progress. Every stage reports actual
acceptance and remaining evidence separately; plan confirmation is not delivery.

##### Recovered Tool Decisions And Current Capability Use

Original July 22 quality reviews and the July 24 terminal synthesis have been
recovered from the predecessor task `019f477e-7aaf-7fd0-837b-41606d7a8b5f` and its
inherited copy in this task. They include more than code counters: security,
packaging, licensing, schema compatibility, time control, memory analysis and
proof publication. Old paths, thresholds, parallel-agent instructions and tool
version claims are historical, not current policy. Their conflicting Vulture
recommendations are resolved by retaining the useful diagnostic question, not
installing a permanent scanner or a dynamic-entrypoint allowlist. The old
request for a tool supply manifest is superseded by native version/lock owners
and the sole gate declaration; it does not revive `system/tools.toml`.

| Capability family | Prior candidates and disposition | Current use and next admissible step |
| --- | --- | --- |
| Size, complexity and change risk | scc for independent measurement; Radon/Xenon rejected as additional permanent policy owners | scc 4.1.0 scanned 478 Python files with complexity/cognitive/unique-line diagnostics. History mode fails on `extensions.worktreeConfig`; repair the tool boundary or use native Git history with exact scope, never alter repository format for the counter. ELOC retains its existing metric owner |
| Code structure and semantic relationships | codebase-memory and Serena; Grimp/import-linter for import boundaries | Rebuilt existing `ethos-current` without a repository artifact: coverage metadata v3 is complete and generation-matched. LSP-backed call edges and clusters are usable; parse gaps, ignored paths, dynamic entrypoints and stale roots still require source verification. Graph results are derived observations, not deletion authority |
| Clone and dead-code diagnosis | find-dup-defs was a pilot, not a proven winner; jscpd/slopo/Vulture/pyscn/redup considered on demand, not simultaneous gates | AST normalization and exact consumer checks found duplicate module parsing and unused fixtures. A maintained external clone tool is admitted only if a bounded sample adds real findings beyond this evidence; no stale whitelist or new control plane |
| Safe transformation | ast-grep and LibCST on demand, not permanent policy; generic generator/framework rejected | Both are locally available. Select one for the actual structural rewrite, retain a reviewable diff and reference closure, then retire scratch transformations |
| Native Python quality | Ruff, Ty, import-linter/Grimp, deptry retained; additional Pylint/Flake8/Black/isort/type-checker policy stacks rejected | Differential Ruff run reports 1636 `D` findings; `ALL` also reports signature, security and structural questions. Do not enable formatter-conflicting rules or convert meaningful asserts/subprocess calls into noise. Review rules by fault and semantic role before accepting the stricter native policy |
| Behavioral and temporal assurance | Hypothesis and scoped mutmut; pytest-deadfixtures diagnostic; time-machine/freezegun versus explicit clock injection | Existing Hypothesis/mutmut are installed. Preserve behavior/state-machine tests and deterministic time boundaries; choose clock/tool support only for an actual uncovered case, not global monkeypatches |
| Runtime and performance diagnosis | Memray/Scalene deferred; tracemalloc and native process/resource observation available | Activate on a retained leak/latency reproduction. Profile the relevant process boundary, account for profiler cost, and prove normal and crash teardown rather than adding permanent profilers to all gates |
| Source and dependency security | Gitleaks and uv audit retained; bounded Semgrep/zizmor pilots; GuardDog/Packj on new-package risk; CodeQL conditional | Verify current native configuration, exact locks/rules/database identity and proof membership first. Do not revive Sonar/Trivy omnibus or multiple overlapping vulnerability/secret inventories |
| Package, SBOM and licenses | validate-pyproject, check-wheel-contents, Twine, REUSE, Syft, SPDX tools-python; Grant only after standard SBOM; Grype/sbomqs conditional | Existing packaging/Syft output is only bounded evidence. Trial a checker against a real malformed artifact, standard violation or license gap; no aggregate quality score or second dependency inventory |
| Public compatibility and provider semantics | Griffe, schema diff and old-instance replay; official GitLab CI Lint; registry-native provenance and cosign only for external blobs | Compare only declared supported public contracts; old Draft-7-only schema tooling is not proof for Draft 2020-12. Keep native provider parsing, execution, signing, uploading and readback separate |
| General semantic graphs | The upstream semantica-agi/semantica describes context and knowledge graphs; its applicability to ETHOS and the originally intended project remain unverified | No installation or framework import is justified yet. Compare a bounded semantic-preservation question against the repaired code graph and original-source review; require measurable additional value without a new ETHOS authority |

The Semantica candidate description was checked against its upstream
semantica-agi/semantica README and docs.getsemantica.ai on September 10.
That establishes the candidate's stated purpose, not tested correctness,
code-reference recall or ETHOS admission; no installation was performed.

The graph coverage defect was reproduced through both MCP and native CLI. A
native rebuild of the same cache repaired missing metadata; code-reference
queries were then checked against known symbols. It did not fix every historical
index, establish complete graph recall, or authorize deleting zero-inbound nodes.
The episodic-memory tool separately failed because its native SQLite binding
was absent; exact original JSONL reads recovered the selected research, but this
is not proof that all historical feedback has been exhaustively restored.

The first execution regression is now demonstrated: `block` and `unknown`
prerequisites previously ran delivery. Shared-runner replacement passes 27
focused cases; duplicate module-name parsing and three unused fixture builders
were removed, leaving measured product/test ELOC 39998/39962 before local-CI
replacement. These are uncommitted focused results, not accepted or global
quality closure. Exact receipts stay in the existing ignored working-evidence
root, with this plan retaining the semantic decisions and remaining obligations.

The private local-CI selection lists and thread scheduler have now been removed.
It uses the shared full closure; missing carrier/security/package checks were
registered without new implementations. The default closure is offline; full
and local CI declare their wider network-dependent evidence honestly. Failed
prerequisites cannot launch delivery, and changing source bytes while HEAD stays
fixed invalidates the receipt. The affected suite passed 147 tests; eight newly
registered native carrier checks actually executed successfully. Changed-source
Ruff and typing pass. These remain uncommitted implementation evidence; full
proof, archive and installed delivery for this Change are still unproved.

At accepted `3e1687cd`, GitLab pipelines 6379/6380 and GitHub main 34431917860
passed. GitHub dev 34431917891 failed only at the concurrent identical ref-intent
writer test: 2804 passed, one failed, one skipped; `ref_intent_lock_timeout`
occurred with eight threads and 32 writes under a one-second lock timeout.
Coverage failure is secondary to that failed test. Investigate critical-section
work and deterministic concurrency, not a blanket retry, longer TTL or weaker
assertion. This independent incident remains urgent next-owner work, not a
claim that socket repair failed or a reason to mix ref-intent changes into
quality selection.

Receipt review reproduced additional false-green boundaries: stable dirty
source could be labeled as HEAD evidence; a passing label with no successful
exit code admitted dependents; preflight/interruption could leave no current
receipt. The transport now requires clean source, validates execution identity
and completeness, and begins with a non-passing record. Dry-run dependency
projection stays unknown. These are focused implementation results, not accepted
delivery. Repeated package-fixture setup was consolidated without removing its
lifecycle, supply, cleanup or diagnostic assertions. Current resource-heavy,
hosted and installed acceptance remain separate obligations.

The September 10 freeze checks passed 135 affected cases, the nine selected
static owners, full Ruff lint/format over 475 Python files, touched-source Ty,
official strict Change validation and native Markdown/prose checks. The actual
local-CI command rejected this dirty worktree before executing any gate and
retained its precise failure receipt. Product/test ELOC is 39999/40000; budgets
were not changed. Gitleaks scanned the tracked mirror with no finding. Syft ran
successfully against the existing accepted wheel at 3e1687cd; this verifies the
owner invocation, not packaging of the uncommitted Change, SPDX conformance,
provenance or publication. Exact-current full proof and delivery remain open.

##### Execution Order And Exit Conditions

1. Close this Change's one execution graph: preserve every effective check,
   declare its evidence plane, remove private local scheduling, and prove
   prerequisite failures, completeness, unique execution and exact source drift.
2. Replace false-green native scopes and overlapping policy owners: Ruff `D`
   and justified stricter rules, actual Ty test/tool scope, correct source metrics
   and thresholds. Preserve source/test ceilings and coverage; remove superseded
   bespoke collectors and shadow configuration.
3. Use measured hotspots, clone evidence, call/import graphs and real fault
   cases for semantic consolidation. Absorb remaining historical lane semantics
   easiest first; retire exact reviewed roots and their unused projections.
4. Close security/package/supply and normal/crash resource obligations at their
   unique owners; reproduce findings across the supported native platform and
   package-only lifecycle boundaries.
5. Finish documentation/decision/configuration/projection agreement and current
   local/remote/installed/adopter evidence. No row is complete merely because
   the present full-proof set passes, a graph is populated, or a tool is installed.

#### ELOC Calibration At `bf825e26`

Read-only measurement using the current owner found the following distribution.
Percentiles use nearest rank over nonzero files; ordinary product excludes
surface modules and tools. These observations do not establish optimal limits.

| Role | Nonzero files | P90 | P95 | Maximum | Current limit |
| --- | --- | --- | --- | --- | --- |
| Ordinary product | 176 | 432 | 461 | 500 | 500 |
| Surface | 19 | 536 | 697 | 697 | 800 |
| Tests | 185 | 467 | 591 | 941 | 1100 |

The config's percentile rationale and 1032-ELOC test maximum are stale. Its
surface allowance assumes thin wiring, but publication and proof commands own
business orchestration. The recommendation, not yet implemented policy, is 500
for product including surface and 800 for tests. First absorb orchestration into
existing use-case owners and organize the publication tests by independent
readiness, branch-transaction and signed-tag obligations. Do not split by size,
copy fixtures or introduce forwarding modules. Reassess against concrete
cohesion and maintenance cost rather than rounding the current maximum upward.

The metric and policy boundary must be repaired before calibration: a bare
string on the same line as an assignment currently excludes that assignment;
multiline string data starting with `#` is treated as a comment. The standalone
size report accepts coerced numbers, silently defaults zero and ignores a rules
parse error. These probes do not prove that other full-proof gates also accept
malformed policy. Enforce positive integer hundred-unit thresholds, distinguish
absent policy from invalid policy, and use one exact source inventory and metric
with the aggregate budget owner. Product/test ceilings follow the conditional
40000-to-45000 authorization above; the project total remains observational. External links in the preceding
chat answer were not retrieved in that turn and are not threshold evidence.

Execute this bounded quality successor after the current retirement boundary;
do not mix it into reviewed-content disposal or add a parallel plan/ledger.

### Accepted-Carrier Lane Handoff Received — 2026-09-08

The original ETHOS thread `019f477e-7aaf-7fd0-837b-41606d7a8b5f` handed its
remaining `work/20260908-accepted-carrier-signature-repair` lane to this existing
terminal-convergence thread `01a00063-d09e-7a71-a52e-a663800a7a0f`. The receiver
read the package and confirmed actual message receipt, separately from Lease
transfer and file-panel visibility. The package's earlier failed delivery status
does not describe the subsequent native-queue delivery. No new task, roadmap,
ledger, or historical `model-promotion` goal is created.

Fresh public status confirms the receiver's exact actor, generation 2, expiry
`2026-09-09T05:31:37.974614+00:00`, and matched authority. The clean lane remains
at `aece154744bc7b2460de1dc478f52ed4426eaa44`, tree
`8da3bdccf19a15da59eaf879cd9eef46ab2ced81`; all 18 transferred file hashes,
the selected refs, and runtime identity match the package. This supersedes the
earlier operational instruction to treat it as an independent peer. Ownership
does not replace fresh exact-path prewrite or prove implementation acceptance.

The handoff bytes have SHA256
`0f1bfcba54df49ae50cbf5696caed822649287b73831795900eb02f0e1f1baea`.
Its recovered historical appendix has SHA256
`bee19e261008d6824bc2ee388ec53613fd61034834e439617e4caa0f4a93aba0`;
that appendix preserves evidence only. Current product meaning, this plan, and
official Change intent supersede obsolete models, commands, dates, and budgets.
Receiver observations remain in the existing working evidence root under
`build/evidence/quality/coverage-floor-focused/signature-handoff-*.json`.

This lane has no accepted delivery. Its last full proof at `9072090bb5cf` blocked;
latest-HEAD proof, archive, landing, and runtime activation remain unproved.
The implementation repairs one accepted tip's signature, not an entire Git DAG.
The easiest retained-topic retirement is complete. Adjudicate this lane's unique
invariants against the existing transaction owner after the two already-reviewed
source disposals, unless a demonstrated prerequisite changes that order;
resolve the quality and archive-task-cycle risks, absorb or replace the necessary
semantics, prove the result, and retire the source lane. Do not blindly merge its
command-private recovery mechanism or make it an adopter-release prerequisite.
The sender has stopped implementation; one receiver owns serial execution, and
AIGW/Proxy remain read-only.

September 9 receiver re-observation supersedes the earlier admission snapshot:
HEAD remains `aece154744bc7b2460de1dc478f52ed4426eaa44`, but public lane status
now blocks on expired Lease and stale candidate base. Historical transfer proves
receipt, not current write authority. No refresh, replay, signing repair or
source-lane mutation was performed; absorption may read its unique semantics
into the currently admitted authoring lane without reviving the old workflow.

### Historical Source-Policy Absorption — 2026-09-08

The archived `historical-source-policy-absorption` Change is accepted at
`4980cf57e1fc28c9c1ae43c8655f18023bc78f14`, included in current `06ea14f0`.
Its semantic comparison covers
the complete three-file dirty increment at historical HEAD
`d66b2df586666afba435a3840cfd40dea8eadc7a`. All 404 added physical lines were
compared through their fifteen added definitions; pre-existing definitions and
the three source-file hashes remain unchanged. Nine definitions match current
ASTs, one matches after its reference-owner rename, and the explicit npm
allowlist test already exists. Three missing boundary cases now extend the
existing policy tests: normalized/forbidden distribution entries, malformed
metadata without invented leak findings, and both historical path/content
surfaces. The historical contributor-role taxonomy is superseded; the current
commit-policy compiler still rejects malformed and unknown old fields.

The five-file focused set passed 101 tests. Five in-process fault substitutions
were rejected by the strengthened tests without editing product source. Targeted
typing exposed six report-consumption diagnostics, including pre-existing ones;
actual shape assertions and one explicit fixture annotation resolve them without
suppression or a replacement report model. Those focused results alone did not
prove acceptance; current accepted source and its exact full proof now contain
the tests. No source worktree retirement follows from that fact alone.

Evidence remains under the existing working evidence root:
`source-policy-semantic-absorption.json`, `source-policy-test-sensitivity.json`,
`source-policy-absorption-focused.log`, and `source-policy-absorption-budget.json`.
The current semantic receipt rechecks all fifteen definitions and the three
source hashes against `06ea14f0`; the ten-path OpenSpec 1.9 input is separately
adjudicated in `historical-openspec-supply-absorption.json`. Both source roots
remain because dirty-content disposal is not yet publicly admitted. Do not
reprove their historical product intent, restore Commitment carriers, or copy
an archive to simulate progress. Bind already-accepted semantic judgment to
fresh exact index, content and resource authority through the existing
retirement owner; then prove actual disposal.

### CI Priority And Preservation Strategy Correction — 2026-09-08

The unaccepted `preserved-worktree-retirement` prototype is withdrawn, not
completed or archived as a successful Change. Its whole-worktree archive would
copy Git-recoverable content, virtual environments, and caches while providing
no consuming transition or executable disposal condition. Its two modified
files are restored to HEAD; its two new modules/tests and five official draft
artifacts are removed. No historical source content, ref, worktree, or Lease is
deleted. Hash-bound withdrawal observations remain in the existing evidence
root until this correction is accepted; the rejected implementation is not
copied into another retention store.

Hosted-verification source repairs are accepted and published at `06ea14f0`,
not waiting for another source freeze. They separate actual gate execution from
interactive candidate/runtime readiness, bind uv's offline interpreter and
repository OpenSpec, retain diagnostics, and validate full gate-set completeness
independently of scheduling order. No coverage floor or gate is relaxed.

| Recurring judgment error | Guardrail in the existing owner | Required verification |
| --- | --- | --- |
| Confuse semantic recovery with reviving a historical lane | Apply Convergence Rule 4; select authoring topology by current authority and isolation need. | Map each unique obligation to its accepted implementation/test or reasoned rejection before source disposal. |
| Treat copying as preservation completion | Keep only unresolved irreplaceable inputs; name consumer and exit condition before retention. | No archive of reproducible supplies; terminal resource absence is observed separately from semantic acceptance. |
| Infer hosted success from local proof or partial tests | Bind each CI receipt to its declared evidence plane and exact expected HEAD. | Regress blocked, malformed, stale-head, and failed-execution observations; inspect both providers after publication. |
| Guess transport, missing tools, or failure causes | Use declared API/Git endpoints and retain actual command, environment, stderr, and artifact facts. | HTTP `192.168.64.101:18086` is the GitLab API; SSH `:1122` is Git transport. Unknown link failures remain unknown until their diagnostics are read. |

September 9 current-head observations supersede the earlier CI checkpoint.
GitHub dev/main runs 34306146235/34306146228 and GitLab dev/main pipelines
6322/6323 all succeed at `bf825e26b07bb6353b8a0fc5777eed399eca3ee1`.
Each GitLab pipeline returned 26 successful jobs. Both forges verify this exact
commit's signature; GitHub reports the expected Yang HENG author and committer.
The configured GitHub and GitLab dev/main refs were independently observed at
that same object. This closes the current accepted commit's hosted CI and
signature observation gaps, not global product or formal release completion.

GitHub main's original package job 102350471173 failed downloading setup-python
during runner initialization: the native Worker log records a TLS unexpected
EOF before repository steps. After the exact endpoint returned HTTP 200, one
failed-job-only rerun produced successful job 102356538803. Do not replay it or
call one successful retry a permanent network repair. Earlier HTTP/2 failures
at `06ea14f0` remain historical evidence, not current-head failures. GitLab's
repository-selected `glab api projects/423/...` route works; explicit hostname
overrides returned 404. No credential or host configuration changed. That 404
does not establish project absence or authorize another authentication setup.

The existing `hosted-ci-convergence-checkpoint.json` owns exact run observations;
it must distinguish source verification, package delivery and provider outcome.
That earlier checkpoint closed publication, runtime activation and hosted
verification for `bf825e26` only. The current `c051743a` delivery and hosted
failures are recorded in the current closeout table above. Detached retirement,
four historical sources and global obligations remain open; none inherits
another source snapshot's proof. New feedback changes this route only when it supplies a missing
invariant, a disproved assumption or changed facts.

## Convergence Rules

1. **Promote before compatibility.** Replace a missing model boundary before
   introducing an alias, fallback, or shim; delete the residue in the same
   bounded change when proof permits.
2. **Compile, do not narrate.** Keep authority, bindings, invalid states, and
   effects in the owning contract and executable verifier; documentation links
   to them as a projection.
3. **Separate planes.** Local proof and each declared peer observation produce
   distinct attestations and cannot imply one another.
4. **Absorb meaning; retire carriers.** The unit of convergence is a valid
   semantic obligation, not a branch or directory. Move unique terminal meaning
   into its current owner in an authorized existing or, when isolation warrants
   it, new Work Lane. Historical lane revival and whole-branch merging are not
   prerequisites. Prove coverage before retiring the source through exact public
   effects. Git-recoverable bytes and reproducible supplies need no duplicate
   archive. Unresolved unique content remains protected with a named consumer,
   next resolving action, and exit condition; uncertainty is not indefinite
   retention authority. Foreign ownership requires handoff, not a new store.
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
