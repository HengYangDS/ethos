## Context

ETHOS currently overlays a renamed vocabulary on several older systems: global
source ranking, a fixed OpenSpec lifecycle, historical re-evaluation, campaign
and decision ledgers, currentness indexes, and coordination models that mix
intent with resources. These systems overlap docs, rules, skills, schemas, CI,
records, and runtime code. They cannot evolve coherently because each can claim
to be the source of current truth.

The canonical target is the common generative kernel in the Product Design
Contract. This change is the ETHOS self-profile implementation carrier, not a
new product ontology.

## Decisions

1. **Two persistent roots.** Commitment is immutable normative intent;
   Attestation is an immutable verifier-bound statement. Facts and
   TransitionPlan are transient. A changed intent creates a new Commitment;
   no amendment chain survives.
2. **Five processing roles.** Every carrier is native, projection, adapter,
   fact, or history. The resolver may emit transient descriptors, but no
   universal manifest, registry, ledger, or index is persisted. Classification
   is operation-selected and does not itself mint authority; an owner validates its
   carrier directly unless a real contextual-resolution consumer needs a
   descriptor, and no operation must manufacture all five roles.
3. **Contextual authority.** Authority/currentness resolves per subject,
   predicate, scope, plane, validity, and context. Global rank, timestamp-only
   selection, `CURRENT`, accepted/superseded directory status, and manual
   indexes are deleted as authority devices. Ambiguity blocks; valid novelty is
   `model_gap`.
4. **One generic transition mechanism.** Observe, extract, resolve, compile,
   evaluate, apply through the effect's strongest native atomic primitive,
   post-observe, attest, then project. Ref and Lease effects use exact CAS;
   worktree, index, and filesystem effects bind exact preconditions and recognize
   an idempotent terminal state without pretending that Git offers CAS for them. Command
   sequences, archive actions, campaign displays, lane phases, and provider
   pipelines are profile projections; no fixed lifecycle is embedded in the
   kernel. A pure, non-persistent Continuation maps current facts to `continue`,
   `await-user`, `blocked`, or `done`, one next action, missing facts or evidence,
   and whether a user decision is required.
5. **Effects close through exact bindings.** A TransitionPlan contains exact
   commitment, fact, prior-attestation, policy, and effect bindings. The adapter
   rechecks preconditions at CAS time. Post-observation and an Attestation—not
   a replayed historical workflow—establish what occurred. Predicate-owned
   evidence binds the claim, normalized command and result, repository identity,
   input/output digests, HEAD, time, and freshness; drift invalidates it.
6. **The kernel is neutral; complete adoption is opinionated.** Commitment,
   Facts, TransitionPlan, and Attestation remain independent of OpenSpec types,
   while every mutation-capable adopter pins verified OpenSpec as the sole
   Change, design, spec, task-progress, dependency, and archive carrier.
   Observation-only repositories may omit it but cannot enter governed mutation.
   “OpenSpec” means its resolved project workflow, not the built-in
   `spec-driven` artifact names: the official schema resolver, project-local
   schemas, artifact DAG, templates, context, per-artifact rules, and
   apply/archive guidance remain authoritative. ETHOS consumes official JSON
   projections without fixing proposal/design/task filenames or duplicating
   schema validation. Schema selection is a repository-local method portfolio,
   not one maximal workflow: minimalist, intent/BDD, event/AsyncAPI, ADR,
   SRS/TDD, release, research, and runbook shapes may compile different artifact
   DAGs for different Changes. Community schemas are candidate source material,
   not installed authorities: native `requires`, generated paths, and `apply`
   prerequisites are enforceable; template prose, evaluator roles, companion
   Skills, gates, and runner state are not unless one existing ETHOS verifier
   owns them. Admit a repository-local schema or selected borrowed pattern only
   when matched workload evidence proves lower ambiguity, time/token cost,
   intent loss, or terminal ELOC without a second task, plan, lifecycle, or
   execution owner. OpenSpec Stores remain outside complete
   adoption because they move the planning root away from the governed
   repository, while generated Skills and slash commands remain projections.
7. **Coordination is derived.** Worktrees, refs, leases, families, inboxes,
   handoffs, candidate queues, records, dashboards, and taxonomies are resource
   facts or projections. They never preserve intent alone. Capacity and
   competition are policy/fact decisions, not fixed cardinalities.
8. **Absorptive evolution.** Every legacy carrier is classified as absorbed,
   historical, or deleted-after-proof. A contradiction/model gap preserves its
   scenarios, promotes the smallest model boundary, recompiles dependents, and
   only then retires residue.
9. **Direct mature capabilities.** Use Pydantic v2 for portable boundary
   contracts, small frozen standard-library values internally, Cyclopts,
   `graphlib.TopologicalSorter`, the selected official CEL engine, native Git
   CAS, and standard supply-chain formats directly. Do not add attrs as a
   parallel model system. Frameworks, generators, Jinja, DI, event buses,
   plugin layers, and workflow runtimes require a concrete consumer,
   conformance evidence, uninstall cleanliness, and net deletion. COMET remains
   benchmark-only or an optional external operator; its Native/Classic runtimes,
   state, hooks, archive, dashboard, Bundle, marketplace, and adapters do not
   enter ETHOS.
10. **One quality owner per property.** Local and hosted execution consume the
    same declarations. Warnings, suppressions, unknown required facts, and
    projection drift fail closed. JSON receives schema validation and canonical
    serialization from its declared owner, not an invented formatter. GitHub
    `act` and the declared GitLab emulator exercise provider projections locally
    but mint only local evidence. The Python product binds one reproducible
    project-local execution closure: `pyproject.toml` declares project and tool
    inputs, `uv.lock` selects the environment, the worktree `.venv` supplies every
    Python executable, Nox owns reusable local/hosted sessions, and Hatchling owns
    builds. Global commands, system site-packages, implicit `PATH` fallbacks, and
    Nox-created duplicate virtual environments are rejected. Nox replaces the
    shell orchestration it subsumes in the same cutover; Tox, Pixi, Pants, and
    Dagger remain rejected until one replaces a retained owner with unique signal,
    offline reproducibility, and further net deletion. Matched
    workflow evaluation uses task × treatment × repetition, control/candidate,
    Pass@k, Pass^k, pollution exclusion, and terminal outcome, cost, recovery,
    intent-loss, mutation, duplication, ELOC, and evidence metrics.
11. **Lossless intent closure.** Accepted feedback is reduced into independent
    semantic obligations before planning artifacts are replaced. Within the
    same authority and scope, a later explicit ruling supersedes an earlier one;
    the earlier ruling remains history and cannot silently return as current
    policy. Every obligation maps to an existing semantic owner, requirement,
    stable task, acceptance condition, and verifier, or records an explicit
    rejection or deferral reason. Unmapped meaning and unresolved contradiction
    are `model_gap` and block retirement and campaign closeout. This closure is
    compiled from tracked carriers and current instructions; it is not another
    persistent ledger or task store.
12. **Stable obligation identity and ordered coordinates.** Numeric task labels
    are continuous phase-local coordinates, not durable semantic identities.
    Refinement preserves each obligation, completed state, and commit or proof
    evidence; coordinate normalization requires an explicit predecessor and
    disposition mapping. A prior obligation sharing that coordinate moves to an
    explicit successor set; if it was completed, at least one successor is a
    completed Foundation identity. Silent reuse, renumbering to reset progress,
    or unmapped deletion is forbidden. The first incomplete task is the campaign
    critical path; every phase has an observable exit condition, and elapsed
    activity without a terminal-state delta is not progress.

13. **Semantic economy governs every carrier.** SSOT, DRY, MECE, SOLID, and
    less-is-more are acceptance tests, not slogans: each retained entity has one
    semantic owner, one reason to change, no overlapping authority, and the
    smallest truthful public and physical surface. No line-count target may erase
    required capability, and no size gate may be evaded through aggregation,
    forwarding, aliases, wrappers, generated displacement, or carrier transfer.
14. **Intent closure is open over the selected Commitment.** Historical IDs are
    evidence for their bounded source only. They do not define the universe of
    accepted feedback and cannot prove the current session complete. Each later
    accepted obligation refines an existing open task, requirement, acceptance
    condition, verifier, or explicit disposition before implementation proceeds;
    no new ledger, plan, Change, or parallel task store is created. Campaign
    closeout fails when any selected obligation lacks that current semantic route.
15. **Portability follows positive value ownership.** Product literals and
    dependencies are admitted by their reason to vary: product invariant, runtime
    input, deployment policy, forge coordinate, publication-trust capability, or
    extension declaration. Personal identities, private products/hosts, local
    paths, keys, fingerprints, ports, provider inventories, and deployment names
    never enter the portable runtime by default. Variation-axis tests replace an
    unbounded blacklist and require ordinary environment, forge, author, install,
    and provider changes without product-runtime edits.
16. **Learning must change the earliest enforceable owner.** Repeated failure,
    review, warning, or workaround is incomplete until it is promoted from incident
    to the narrow rule, gate, schema/default, scaffold, or generator that makes the
    correct path normal and the invalid path fail closed. Reflection text, memory,
    or a skill alone is not prevention. Superseded lower carriers are removed after
    proof so learning does not become another accumulation surface.
17. **Campaigns project atomic Changes.** A Campaign has no carrier, tasks, or
    lifecycle state of its own. It is reconstructed from accepted OpenSpec
    Changes and `Commitment.dependencies`. One Change and one short Work Lane own
    one independently useful result. If a proved subset can land while another
    acceptance obligation remains open, the latter is a successor rather than
    more scope in the same lane.
18. **Intent is compiled, not rediscovered or duplicated.** For each atomic
    Change, official OpenSpec status, instructions, artifact dependencies,
    project context, artifact rules, completed artifacts, and selected
    Commitment are the inputs to one transient intent context. It derives
    ambiguities, assumptions, invariants, negative scope, affected capabilities,
    requirement-to-task-to-proof edges, and unresolved contradictions before
    mutation. Missing material meaning is `model_gap`; generated agent context,
    Skills, slash commands, MCP resources, code graphs, annotations, and reports
    are disposable projections, never another intent store. Impact compilation
    may later consume a proved code/spec graph, but only when it replaces search
    and mapping code with better recall and lower token/time cost.

## Carrier Disposition

This is the cutover inventory, not a new registry. Each row classifies one
MECE carrier family by an ordered tracked-path selector, names its current
semantic owner, and binds unresolved work to the existing campaign task that
must close before retirement. Earlier narrow selectors take precedence over
the final explicit remainder; every tracked path resolves to exactly one row.

| Selector | Carrier family | Disposition | Current owner | Remaining task | Acceptance / verifier |
| --- | --- | --- | --- | --- | --- |
| `docs/governance/product-design-contract.md`, `system/**` | Canonical product contract and machine declarations | absorbed | product contract and narrow machine declarations | `5.2` | design integrity, schema, and projection-drift gates |
| `openspec/changes/terminal-convergence/**` | Active terminal OpenSpec Change | absorbed | official OpenSpec workspace plus this self-profile Change | `6.10` | official strict validation and owner-native archive |
| `openspec/specs/**` | Accepted OpenSpec capability specs | deleted-after-proof | active terminal delta specs, then canonical capability specs | `5.1` | canonical spec cutover with no resurrected lifecycle owner |
| `openspec/changes/archive/**` | Official OpenSpec archives | historical | immutable Git history | `5.6` | active readers exclude archives from authority |
| `evidence/**` | Claims, Chronicle, and legacy evidence bytes | historical | immutable evidence plus future Attestation disposition | `5.6` | no current reader or policy authorizes legacy evidence |
| `docs/history/**` | Superseded documentation history | historical | Git history and current documentation routing | `5.6` | links resolve and current docs exclude historical authority |
| `docs/governance/conversation-ledger.md` | Conversation-derived requirement ledger | deleted-after-proof | this design, delta specs, stable tasks, and the fact-boundary closure below | `0.4` | all feedback and independent fact boundaries map to one owner and verifier |
| `docs/plans/terminal-governance-product-design.md` | Canonical terminal target design | absorbed | terminal target design under the Product Design Contract | `5.1`, `5.6` | design integrity preserves the target until its current semantics are absorbed |
| Superseded plans and experimental research | Historical design carriers | deleted-after-proof | Git history plus current OpenSpec design/tasks | `5.4`, `5.6` | current design already absorbs lane, runtime, and tooling conclusions; stale carriers are removed rather than archived in parallel |
| `.agents/**`, `.config/**`, `.github/**`, `.gitlab/**`, `.gitlab-ci.yml`, `.githooks/**`, `.pre-commit-config.yaml`, `rules/**` | Rules, skills, checks, forge, hook, and provider projections | absorbed | their declared native owners | `5.5`, `5.7` | route-owner, drift, and provider-homomorphism checks |
| `.ethos/**`, `.gitignore`, `.gitleaks.toml`, `AGENTS.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSE`, `README.md`, `assets/**`, `distributions/**`, `docs/**`, `openspec/README.md`, `openspec/config.yaml`, `openspec/changes/*`, `package-lock.json`, `package.json`, `pyproject.toml`, `ruff.toml`, `src/**`, `tests/**`, `tools/**`, `uv.lock` excluding every earlier selector | Remaining tracked product, documentation, source, tests, tools, distributions, and root declarations | absorbed | the narrow owner selected by routing and module boundaries | `5.1`, `5.3`, `6.1`, `6.6` | tracked-path partition, import boundaries, repository audit, and full proof |
| linked `work/*` resources outside the tracked tree | Auxiliary and superseded Work Lanes | deleted-after-proof | exact native lane lifecycle | `0.7`, `4.6`, `7.2` | semantic absorption first; holder authority and exact retirement receipt independently |

Deletion blocks while the named remaining task, a consumer, an independent
semantic delta, or a `model_gap` remains. A historical disposition preserves
bytes but grants no current authority.

Task `0.7` is one outcome with two ordered admissions: campaign bytes are
committed and equivalence-proved first; authority-bound retirement follows only
after the auxiliary dirty bytes, holder, Lease, and exact target state are
admitted. The second admission cannot erase or postpone the first, while the
task remains incomplete until the native retirement receipt exists.

### Official OpenSpec 1.7 Cutover

Tasks `4.1` and `6.10` own one no-compatibility cutover to OpenSpec `1.7.0`.
The repository pin and effective executable must agree; a cache-selected or
machine-global version cannot override the declaration. The adapter consumes
official `list`, `status`, `validate`, and `archive` JSON, including nested spec
identities, artifact `requires`, valid `skip_specs`, archive warnings, no-op
updates, and the returned archive path. ETHOS does not enable a global default
store or retain a parallel 1.6 reader.

OpenSpec owns proposal, specs, design, tasks-progress, Change identity, artifact
dependencies, generated Skills, and archive lifecycle for every complete
adopter. ETHOS owns admission, Work Lanes and Leases, proof and Attestation,
Git CAS, land, and publish. Official Skills are projections only. Another SDD
runtime may be an external method/operator only when a real consumer proves net
deletion, no second SSOT, clean recovery, and measurable time/token benefit;
Spec Kit is not a kernel dependency and COMET remains only such a candidate.

OpenSpec customization is a governed product surface, not a compatibility
escape hatch. Its native layers are project context/rules/operation guidance,
the selected artifact schema, and reusable schema bundles. The selected schema
may vary by Change because a defect, refactor, product feature, research task,
event contract, release, and end-to-end runbook do not have the same irreducible
information needs. ETHOS therefore does not impose one universal artifact graph
or preserve a registry of framework adapters. It observes the schema resolved by
the pinned official CLI and admits mutation only when the effective schema is
reproducible from the pinned OpenSpec package or tracked project bytes. A
user-global schema is useful for authoring and discovery but must be materialized
into the repository before it can govern a complete adopter; otherwise another
machine cannot reproduce the Change from Git.

Community workflows are evaluated as mechanism specimens, not trusted packages.
The surveyed set includes Superpowers bridges; minimalist, intent-, behaviour-,
event-, ADR-, SRS-, TDD-, question/research-, subagent-, human-gate-, bugfix-,
refactor-, feature-, release-, full-cycle-, and end-to-end-runbook schemas. Their
reusable contribution falls into four distinct classes:

1. artifact topology natively enforced by OpenSpec through `requires`, output
   paths, `apply.requires`, and tracked task files;
2. artifact grammar conveyed by templates, context, and rules but requiring a
   separate parser or verifier for mechanical enforcement;
3. execution method delegated to an optional Skill, agent host, reviewer, or
   external command and therefore unavailable when that capability is absent;
4. extension fields or prose claims that the official runtime does not interpret
   and that provide no governance guarantee.

Schema admission first classifies every claimed mechanism into those classes,
then checks semantic fit, unique ownership, hermetic resolution, validation,
uninstall cleanliness, and measured terminal cost. Promotion to a bootstrap
default additionally requires matched evaluation against `spec-driven` and net
deletion across source, tests, tools, and documentation. This permits deep
OpenSpec customization without mistaking a long prompt, an installed plugin, or
an ignored YAML key for enforcement.

The owner-native archive is the final tracked source mutation, not the final
proof claim. It changes HEAD, so local proof, proposal/hosted verification, and
dual-provider publication execute once on the post-archive commit. The archived
task bodies preserve execution history only; accepted capability specs and fresh
Facts recompile the Phase 7 effects, whose completion is stated only by HEAD-bound
Attestations and receipts. Archived history is neither authority nor a progress
store.

The reachable edge is `ethos lane archive-change`, a semantically namespaced
transaction rather than a seventh public root. It verifies the current
same-holder Lease, exact HEAD/tree, completed official status, strict validation,
and pre-archive proof; invokes only the pinned OpenSpec `1.7.0`; validates the
exact rename and canonical-spec delta; commits through normal hooks; advances
the Lease to the archived Commitment; and emits a typed Attestation. This removes
the former split ownership among an external mutation, later Git commit, and
separate Lease repair. Post-archive plan/proof/land consume the archived
Commitment only as the exact lane intent binding, never as current spec authority.

### Independent Fact-Boundary Closure

The superseded ledger also contained constraints outside CL-001 through CL-025.
They close here rather than surviving as a second current document.

| Constraint | Disposition | Current owner / task | Verifier |
| --- | --- | --- | --- |
| Product behavior uses one `src/ethos` distribution with narrow modules; adopter semantics remain in profiles or adopter repositories | superseded | product boundary and isomorphic adopter governance; `F.3`, `3.5`, `5.3`, `6.7` | package, module-boundary, and three-adopter gates |
| Domain contracts remain profile data rather than ETHOS assumptions | absorbed | product contract and profile schemas; `6.7`, `6.8` | profile isolation and schema conformance |
| Superpowers and host capabilities remain optional observations, never durable repository truth | absorbed | product contract and method-pack boundary; `F.7`, `4.4`, `5.5` | authority and method-pack architecture tests |
| Complete adopters require OpenSpec as the sole Change/SDD carrier while the kernel remains vendor-neutral | absorbed | adoption and OpenSpec boundary; `F.9`, `4.1`, `5.5`, `6.7`, `6.10` | pinned 1.7 characterization, three-adopter lifecycle, and archive receipt |
| Backlog, execution runtimes, generators, and scaffolds require a proved consumer and net deletion | deferred | adapter admission; `6.9` | consumer, uninstall, and dependency gates |
| Product behavior does not migrate into `tools/`; adopter `tools/agent` content is classified during adoption | absorbed | semantic module ownership and adopter classification; `5.3`, `6.7` | module-boundary and adopter report gates |
| `.mailmap` and package-root re-exports remain absent | absorbed | repository hygiene; `6.6` | architecture scans |
| SSOT, DRY, MECE, SOLID, less-is-more, high cohesion, and low coupling apply across every carrier | absorbed | semantic economy, native ownership, and terminal compression; `3.1` through `6.6` | owner partition, duplicate/dependency, module-boundary, and source-budget gates |
| GitLab and GitHub are independent complete CI/CD and distribution planes over one portable semantic contract | absorbed | provider projection and proof separation; `5.7`, `7.3`, `7.4` | provider-homomorphism and independent hosted Attestations |
| Local GitHub `act` and GitLab emulation prove local projection behavior only | absorbed | native quality owners and assurance-plane separation; `6.1`, `6.4`, `7.1` | locked local-emulator gates plus hosted non-substitution tests |
| Tox, Nox, Pixi, Pants, and Dagger do not enter the product without unique signal, a real consumer, and proved net deletion | deferred | quality/tool admission; `6.1`, `6.5`, `6.9` | matched replacement prototype, offline lock proof, and uninstall/dependency gates |
| Retired Subject/Contract/Transition/Inscription/Chronicle/Evolve vocabulary does not define the terminal kernel | superseded | Commitment, Facts, TransitionPlan, Attestation, and model promotion; `1.1` through `3.2` | kernel contract, authority, and lifecycle tests |

This table and CL-001 through CL-025 close the retired ledger only. They are not a
complete-session manifest. Later accepted feedback is authoritative through the
selected Commitment and is absorbed directly into the current Decisions, task
bodies, delta requirements, acceptance conditions, and verifiers. Any accepted
obligation that cannot be routed there is a `model_gap` and blocks the affected
task and campaign closeout rather than being silently omitted.

## Accepted Feedback Closure

The superseded conversation ledger is reduced here into current semantic
owners. `deferred` means a concrete consumer must first satisfy task `6.9`;
`superseded` means a later explicit terminal decision replaced the old shape
without dropping its underlying concern. The retired source remains auditable at
`5093e95db^:docs/governance/conversation-ledger.md`; it is evidence, not an owner.
Later accepted rulings are preserved below in the independent-boundary and
post-cutover refinement tables rather than appended to another ledger.

| Feedback | Accepted obligation | Disposition | Current tasks | Current semantic owner or reason | Verifier |
| --- | --- | --- | --- | --- | --- |
| CL-001 | Keep orchestration thin and split code by narrow semantic ownership. | superseded | `5.3` | one `src/ethos` distribution with narrow semantic modules replaces package-count design | module-boundary and import-linter gates |
| CL-002 | Skills must meet provider-quality expectations rather than remain placeholders. | absorbed | `5.5`, `6.7` | skill quality and adopter proof | skill portfolio and adopter gates |
| CL-003 | `activation.toml` is an ETHOS registry, never provider metadata. | absorbed | `5.5` | skill activation remains a repository registry, never provider metadata | skill schema and projection-drift gates |
| CL-004 | Superpowers remains optional execution method, not repository truth. | absorbed | `F.7`, `5.5` | Superpowers remains an optional observable method pack | method-pack authority architecture test |
| CL-005 | Host memory, goals, subagents, modes, and diagnostics are capability facts only. | deferred | `4.4`, `6.9` | host capabilities are optional facts or adapters and never repository truth | profile/adopter conformance |
| CL-006 | Backlog intake may be an adapter but cannot own proof or contract truth. | deferred | `6.9` | backlog intake requires a real adopter proving unique need and net deletion | adapter admission and uninstall proof |
| CL-007 | Classify adopter agent tools explicitly as profile, projection, or residue. | absorbed | `6.7` | adoption classifies native tool surfaces without productizing adopter vocabulary | three-adopter adoption reports |
| CL-008 | Use the official OpenSpec lifecycle for Change artifacts and archive. | superseded | `F.9`, `4.1`, `6.10` | official OpenSpec owns the complete adopter Change lifecycle; ETHOS owns admission, proof, and effects | official strict validation and lifecycle tests |
| CL-009 | Keep spec capabilities MECE while allowing their taxonomy to evolve. | absorbed | `5.5` | capability coverage, overlap, novelty, and retirement checks evolve the taxonomy | spec coverage and overlap gates |
| CL-010 | Turn hypotheses, experiments, feedback, and retirement into real evolution. | superseded | `2.1`, `3.2`, `5.2` | open predicates, model promotion, and Attestations replace an evolution ledger runtime | model-gap and Attestation tests |
| CL-011 | One real compiler and runner plans, evaluates, executes, and evidences gates. | absorbed | `3.1`, `6.1` | one TransitionPlan compiler and declared gate owners | plan determinism and gate execution tests |
| CL-012 | Govern formatting, generated artifacts, and evidence locations. | absorbed | `6.1`, `6.4` | native format, artifact, evidence, and projection owners | full quality proof |
| CL-013 | Reference adopters stay profile-bound and cannot shape the product runtime. | absorbed | `6.7` | three profile-bound reference adopter shapes | adopter conformance suite |
| CL-014 | Domain contracts remain profile or adopter semantics. | absorbed | `6.7`, `6.8` | portable contracts and profiles keep domain semantics outside the product | profile isolation and schema conformance |
| CL-015 | Keep local, protected-ref, hosted, break-glass, and publication proof distinct. | absorbed | `7.1`, `7.2`, `7.3`, `7.4` | local, protected-ref, hosted, and publication proof remain separate planes | terminal closeout receipts |
| CL-016 | Verify commit signatures independently on each hosted provider. | absorbed | `7.4` | each provider verifies its own hosted signature and release facts | GitLab and GitHub release observations |
| CL-017 | Do not restore repository-level `.mailmap` identity rewriting. | absorbed | `6.6` | repository hygiene forbids `.mailmap` unless a future explicit design changes the owner | repository hygiene architecture test |
| CL-018 | Treat history rewriting only as an explicitly authorized migration. | rejected | `6.9` | history rewrite is not a standing product mechanism; any migration requires a separately admitted consumer | product-boundary gate |
| CL-019 | Make documentation clear, faithful, elegant, navigable, and strongly organized. | absorbed | `5.1`, `5.4` | canonical information architecture and flat DR grammar | docs registry, links, and DR grammar |
| CL-020 | Bind adopters through strict profiles without multiplying full skeletons. | superseded | `6.7` | strict profiles bind native repositories without full-skeleton generation | profile round-trip and conflict tests |
| CL-021 | Make npm packaging, installation, and publication independently real. | absorbed | `6.7`, `7.4` | Node/polyglot adopter and dual-provider artifact proof own npm distribution quality | npm pack, install, and publication receipts |
| CL-022 | Preserve one small ETHOS-first public command plane. | absorbed | `F.5` | the six Cyclopts roots are the sole public command plane | live Cyclopts architecture test |
| CL-023 | Feed hosted parity into evidence without creating another truth store. | absorbed | `7.3`, `7.4` | hosted results enter as plane-bound Attestations, never a second truth store | independent provider Attestations |
| CL-024 | Make every admitted standard executable, evidenced, and removable. | absorbed | `6.1`, `6.9` | standards have one admitted owner, bounded evidence, exit strategy, and consumer | tool admission and dependency gates |
| CL-025 | Keep accepted feedback auditable so scope cannot silently narrow or vanish. | superseded | `0.4`, `0.5` | structural history and intent checks replace a permanent conversation ledger | intent-closure architecture test |

## Pre-cutover Task Closure

Commit `b23dc97cd92675bd3a6f58c13a1ec73c7f4ba2c6` closes the period in
which obligation identity was repeatedly rewritten. The grouped rows below
preserve every changed, reset, or removed pre-cutover obligation. From that
commit forward, an obligation body is immutable, completion only advances, and
coordinate normalization requires an explicit predecessor and disposition row
here.

| Historical tasks | Disposition | Current tasks | Evidence or ruling |
| --- | --- | --- | --- |
| `0.1` | absorbed | `0.1`, `F.8`, `F.17`, `F.18`, `F.19` | current binding retains the Change and lane; completed foundations retain branch roles, exact Lease and Commitment bindings, and observe-only foreign-lane state; the old accepted/candidate snapshot and concern matrix remain historical evidence rather than mutable authority |
| `0.2` | absorbed | `F.10` | `351e026fab`; hard source-budget gaps block |
| `0.3` | absorbed | `F.11` | `1d98cce8dc`; score readiness and report authority are deleted |
| `0.6` | absorbed | `0.6`, `F.9` | the completed deletion obligation and fail-closed official active-change selection jointly retain the later reporter-path clarification |
| `1.1` | absorbed | `F.1` | `351e026fab`; direct source measurement owns the property |
| `1.2` | superseded | `5.3`, `6.5`, `6.6`, `6.9` | deletion is governed by semantic boundary and proved consumer need, not a fixed file list |
| `1.3` | absorbed | `F.2`, `3.5` | `9e794bcc22`; positive product ownership replaces private-product coupling |
| `1.4` | absorbed | `F.12`, `6.3` | `271cb4a9b9`; historical measurement is preserved and terminal limits remain active |
| `1.5` | absorbed | `F.7` | `2a07f9e434`; optional runtimes cannot own tasks or progress |
| `1.6` | superseded | `5.1`, `5.2`, `5.5`, `5.6` | absorptive knowledge retirement replaces bulk carrier deletion |
| `1.6.1` | absorbed | `F.19` | `ceb40e38f1`; closeout-residue currentness was removed |
| `2.1` | absorbed | `F.13` | `271cb4a9b9`; kernel contract and determinism tests landed |
| `2.2` | absorbed | `F.14`, `1.5`, `1.6` | `271cb4a9b9`; Pydantic and graphlib foundation remains while terminal model cutover continues |
| `2.3` | absorbed | `F.4` | `a21de4a397`; one official CEL engine remains |
| `2.4` | absorbed | `F.3` | `5388fe581f`; one top-level distribution remains |
| `2.5` | superseded | `1.1`, `1.2`, `1.3`, `2.3` | two persistent roots and transient Facts/TransitionPlan replace stored read models |
| `3.1` | absorbed | `3.1`, `3.3` | pure compilation and exact Git effects remain separate owners |
| `3.1.1` | absorbed | `F.15` | `271cb4a9b9`; lifecycle declarations collapsed to one owner |
| `3.1.2` | absorbed | `3.3` | exact idempotent Git effect boundary remains open |
| `3.2` | superseded | `4.2`, `4.3` | fixed WIP, competitor counts, and mutable intent amendments are rejected |
| `3.3` | absorbed | `4.4` | vendor-neutral handoff, takeover, recovery, and inbox reconstruction remain open |
| `3.3.1` | absorbed | `F.16` | `271cb4a9b9`; lifecycle observation uses one isolated Git profile |
| `3.3.2`, `3.3.3` | absorbed | `4.4` | exact takeover and transcript-free continuity are one current obligation |
| `3.3.4` | absorbed | `F.17` | `db210a46c8`; strict full-row Lease CAS landed |
| `3.3.5` | absorbed | `F.18` | `db210a46c8`; source-root carrier materialization landed |
| `3.4` | absorbed | `4.5` | adaptive proof and short candidate CAS remain open |
| `3.5` | absorbed | `F.8` | `e3bc687e55`; `proposal/*` is the sole remote review role |
| `3.6` | absorbed | `3.6` | bounded property, mutation, and formal proof remain open |
| `3.7` | deferred | `6.9` | an execution backend requires a measured real consumer |
| `4.1` | superseded | `6.1`, `6.5` | one owner per property replaces a fixed tool shopping list |
| `4.2` | absorbed | `6.2` | all warnings and suppressions remain terminal blockers |
| `4.3` | absorbed | `6.3` | exact ELOC and branch-coverage floors remain open |
| `4.4` | superseded | `3.6`, `6.5` | mutation and duplicate tools are admitted only for distinct signal |
| `4.5` | superseded | `6.1`, `7.1`, `7.4` | supply-chain formats and local replay require exact proved claims |
| `4.6` | absorbed | `6.3` | terminal ELOC thresholds remain exact |
| `4.7` | absorbed | `F.6`, `5.3`, `6.6` | `78faa3318f`; semantic and physical boundaries remain enforced |
| `5.1`, `5.2`, `5.3`, `5.4` | absorbed | `6.7` | one task now proves all three adopter shapes and isolation properties |
| `6.1`, `6.2` | absorbed | `1.6`, `6.8` | generated schemas and one conformance kit own portable contracts |
| `6.3` | superseded | `4.4`, `6.8`, `6.9` | protocol adapters are optional; catalogs and packs need a real consumer |
| `6.4` | deferred | `6.9` | Jinja or scaffolding is admitted only when it proves net deletion |
| `7.1` | absorbed | `7.1` | immutable local full proof remains the remote-mutation admission |
| `7.2` | absorbed | `7.3` | one proposal and two independent hosted planes remain required |
| `7.3` | absorbed | `7.4` | protected refs, release, tag, and artifacts bind one commit |
| `7.4` | absorbed | `7.2` | local candidate/dev closeout and lane retirement precede proposal publication |
| `7.5` | superseded | `6.10` | official OpenSpec archive is the last source mutation before the sole proof and provider publication sequence |
| `0.2.1` | superseded | `0.2` | normalize the current Phase 0 coordinate after the legacy `0.2` source-budget obligation moved permanently to `F.10` |
| `0.3.1` | superseded | `0.3` | normalize the current Phase 0 coordinate after the legacy `0.3` readiness obligation moved permanently to `F.11` |

## Post-cutover Task Refinement

`tasks.md` remains the sole current execution truth. This table records only
exact historical body transitions required to absorb later explicit rulings;
it cannot set completion, priority, or progress. Every body change after the
cutover must bind its task coordinate and normalized predecessor/successor
SHA-256 here, completed task bodies remain immutable, completion never moves
backward, and an unobserved or unregistered row fails the architecture gate.

| Task | Prior body SHA-256 | Successor body SHA-256 | Disposition | Ruling |
| --- | --- | --- | --- | --- |
| `2.1` | `f1152551ce2a0c177e6be6873e10a1e9984caa7ee4f4d3ae5a3a5fa8b69efdbd` | `a4442bf4be9d6e836916542c8f177766bafe37d1bbb64feef5e1956c39bd5bb9` | clarified | Five roles are owner-local processing classifications; only a real contextual-resolution consumer justifies a transient descriptor. |
| `4.1` | `b7918d4d35027a9193c1b5424b1abfe58ddd11f44fa824b2c751782cfa942e7c` | `b301e40fa59dc5bd192d169f033515d9879e78ec8d1a50a17dceca1884c5a3da` | clarified | OpenSpec 1.7 characterization, nested specs, artifact dependencies, and removal of the 1.6 reader became explicit acceptance obligations. |
| `6.10` | `9fe10d07717cf56b5696e8e4fc0ed91737e060de10e8e89121f78ba01a0d49c6` | `6dfc3d418c1b630624d1281111cf564cc6dc1f605b80ed511fe184c70a8c8905` | clarified | Official 1.7 archive edge cases and fail-closed validation became explicit acceptance obligations. |
| `4.1` | `b301e40fa59dc5bd192d169f033515d9879e78ec8d1a50a17dceca1884c5a3da` | `3c12cf104f3867dbe7e926b9622390117c81b008cc496bc693ab73eae817e64f` | superseded | The later product ruling keeps the kernel vendor-neutral but requires verified OpenSpec for every mutation-capable complete adopter. |
| `5.5` | `2dc34a5e4de059a8618df1f59425c54274d72774235e8aa7f11e27f210238c6b` | `ca758f3eca189fda18b6607775156f998eb4eb1ee67cf556d7a434ceae5d8b0d` | clarified | Official OpenSpec Skills are generated projections and cannot own task or lifecycle authority. |
| `6.1` | `d1af42bbc127276837574e07e7119acf7abe0f5d01f3bfd3c6b36d0be1e2cc0d` | `e27506e17c7d959264d3a94f0e5d92f49fc791ba414d9b42aeb7326143229001` | clarified | Direct dependency floors, immutable non-Python identities, and lock ownership became explicit supply-chain obligations. |
| `6.5` | `69b7dbe3409998637d2c193c19cc5830fdd774829d2ad35340963baeab2a39a0` | `a0877a0bd062cd77cdf546c3f8fe11b220399626382832aa2bdbbdf93ae5213a` | clarified | One online refresh owns latest-stable proposals while normal proof remains offline and lock-bound. |
| `6.7` | `6176a543b092c496d3f098e539fc0e4afb287c77bd507abeaa4295f3fa7192f6` | `9c76a47117bceb83cf2e0490d1d940cb75d4b4d4765f1504a8dd64f3b3517b5e` | superseded | The later adoption ruling limits no-OpenSpec operation to observation-only repositories and requires the full OpenSpec lifecycle for governed mutation. |
| `6.9` | `a17de7104426643874350289628855d3c8b771467669b7ec5b3f6ee155c0034a` | `7144cc607c7c0f178601edc7eb7744565b695b7aede85d4b21733426b7405456` | clarified | Spec Kit is excluded from the kernel and COMET remains only an external candidate under the existing consumer and net-deletion bar. |
| `6.10` | `6dfc3d418c1b630624d1281111cf564cc6dc1f605b80ed511fe184c70a8c8905` | `4f126e51c7c545b72e4bb02c17847ef5faa25e5b590a7af2389045c392ae72bd` | clarified | The archive receipt must bind the exact effective OpenSpec 1.7 executable and tool version. |
| `1.2` | `3da810636aace7bd592059ee706ac023fed52f9e5eaa8e5e0eaa00eea8106a4b` | `cd8f47c9dc73f89cb647a9bba976c02f61efa5000fb0ec3a16653d63b84e69e4` | clarified | Typed evidence and freshness extend the existing open Attestation envelope without adding a receipt entity. |
| `3.1` | `db804e65e4475aa5863b1eb8602526bd3979ca9426e5cb90216cbf2758b4d9de` | `e4bbb661802e5ca57de3d93f350a424234497873693f01fa33548e39511a50f1` | clarified | Continuation is one pure projection from authoritative facts, not persisted lifecycle state. |
| `5.5` | `ca758f3eca189fda18b6607775156f998eb4eb1ee67cf556d7a434ceae5d8b0d` | `3eb71b9c00f031cebdffcc52c08727cce3e38b7e0bfef7ff9707f8fc76d21356` | clarified | Workflow evaluation remains evidence for evolving skills and practices, never progress authority. |
| `6.9` | `7144cc607c7c0f178601edc7eb7744565b695b7aede85d4b21733426b7405456` | `d2f2fccced730430a150670f75b1930e1d6d5ca6821e6244104044260c846db4` | clarified | COMET contributes benchmark and mechanism ideas only; semantic progress, retry convergence, and matched evaluation stay ETHOS-owned. |
| `6.4` | `9f9ffa71983c85d75101047a86e67f941694690e1398961a0867f30be3f771a8` | `7d8645ac2f2d32cb79160381868fbf7e21c6c35ef39a34791f17918c8cfac280` | clarified | Local `act` and GitLab emulation exercise provider projections but mint only local evidence. |
| `3.1` | `e4bbb661802e5ca57de3d93f350a424234497873693f01fa33548e39511a50f1` | `ea3f95a7ea26ec36f8d35e7e95fa17f07846adfde9321f871e19e11be460d3bc` | clarified | Terminal semantic deletion, not intermediate diff size or activity, measures the transaction cutover; bounded temporary growth cannot survive as a parallel path. |
| `3.4` | `7f98df1ca887bc8186a1d6a6be4f130be68ac325d056009bde211252376d4f27` | `888f848059fd4aa6a877bd78fbc271cdc5596575e73b8e7a683d92aacf7ac851` | clarified | Positive ownership classifies portable values and variation axes instead of expanding a blacklist for every leaked environment literal. |
| `3.5` | `7c6ffe539adeba2a9430fbc09bc21ff751382e2c7babcd3406caba7ed7932cd3` | `2dc2ff7f084ee85439e3bf4268f3d40c535d3a67798541674d7650e4c8449e0d` | clarified | Private-product and workstation coupling is absent from every product carrier, not only runtime source. |
| `5.5` | `3eb71b9c00f031cebdffcc52c08727cce3e38b7e0bfef7ff9707f8fc76d21356` | `a302ac2efca054f87bae8e623fbc9497075cff154815ea3b1bd68e145dea4f4b` | clarified | Learning and repeated findings must change the earliest enforceable semantic owner and retire obsolete lower carriers. |
| `5.7` | `829c0724aeed48520f0bd5d74e69ade7428f3bbfda562799b26f9b8d647b0d7e` | `92585ca2e28280f112e2447ea2feff76a041f31639824869411364f37355ecb7` | clarified | Provider homomorphism covers issue/review policy and the exact local-only and remotely publishable branch roles. |
| `6.1` | `e27506e17c7d959264d3a94f0e5d92f49fc791ba414d9b42aeb7326143229001` | `ecaef0a7832fd54287f442a1e0d5fa6f0a97ea00ebe71c1cdd992ec32e3a47d6` | superseded | The later environment ruling combines hermetic fixtures with one worktree `.venv`, uv lock, Nox session owner, and Hatchling build owner while subsumed shell orchestration is deleted. |
| `6.5` | `a0877a0bd062cd77cdf546c3f8fe11b220399626382832aa2bdbbdf93ae5213a` | `bd8bf1e582d525a982a8735cfd728a7fe2c07a69f72050bcb04d42095edbbcd5` | clarified | Duplicate and structural tool candidates are compared by unique signal and net deletion rather than accumulated by name. |
| `6.7` | `9c76a47117bceb83cf2e0490d1d940cb75d4b4d4765f1504a8dd64f3b3517b5e` | `ff699ef143dde1907b3d01b7b6426e55dfcfcf0885bdae74e3a15725ee4bc946` | clarified | Adopter proof includes first-hour CLI, SDK, JSON, scaffold, diagnostic, and recovery UX without repository-shape cloning. |

## Requirement To Task To Proof

This table is the explicit lossless edge set consumed by `ethos plan`. It does
not own progress: requirement text remains in delta specs, task state remains in
`tasks.md`, and each proof name resolves to an existing gate or acceptance
boundary. A missing or stale edge is `model_gap`.

| Requirement | Task | Proof |
| --- | --- | --- |
| `adapters:Exact-request Mutation Admission` | `3.1` | `unit-admission` |
| `adapters:Bounded External Evidence Adapters` | `3.6` | `unit-evidence` |
| `adapters:Official OpenSpec Lifecycle Adapter` | `4.1` | `openspec` |
| `adapters:Optional tool adapters remain replaceable` | `6.9` | `product-boundary` |
| `assistant-projections:Projection Boundary` | `4.3` | `unit-projections` |
| `assistant-projections:Terminal assistant projections are derived, not root configuration` | `5.5` | `playbooks-v2` |
| `command-plane:Public Command Plane` | `F.5` | `unit-cli` |
| `command-plane:Proof Command State Semantics` | `7.1` | `full-proof` |
| `command-plane:Explain Command Projects Invalid-State Signals` | `3.2` | `unit-cli` |
| `command-plane:Self OpenSpec Lifecycle Mode` | `4.1` | `openspec` |
| `command-plane:ETHOS OpenSpec adapter remains under one command plane` | `4.1` | `openspec` |
| `contracts:Provider-neutral Contracts` | `6.8` | `schemas` |
| `contracts:Governed Repository Context Contract` | `6.7` | `adopter-conformance` |
| `contracts:TransitionPlan Boundary Semantics` | `3.1` | `unit-plan` |
| `contracts:Portable Conformance Surface` | `6.8` | `schemas` |
| `distribution:Published Distribution Boundary` | `7.4` | `release-proof` |
| `distribution:Release configuration advertises only active policy` | `5.7` | `release-config` |
| `distribution:Single Terminal Campaign Publication` | `7.4` | `release-proof` |
| `kernel:Closed Verdict Reduction` | `1.4` | `unit-verdict` |
| `kernel:Minimal Semantic Kernel` | `1.1` | `unit-kernel` |
| `kernel:Semantic attestation is receipt-bound and non-authorizing` | `1.2` | `unit-attestation` |
| `kernel:Root Interpretation Boundary` | `2.1` | `unit-kernel` |
| `proof-hosts:Proof Separation` | `7.1` | `full-proof` |
| `proof-hosts:Product Migration Closure Proof` | `6.7` | `adopter-conformance` |
| `quality:One Owner Per Property` | `6.1` | `quality-profile` |
| `quality:Warning And Suppression Zero` | `6.2` | `zero-warning` |
| `quality:Native Carrier Quality` | `6.4` | `format-quality` |
| `quality:Terminal Compression And Test Floor` | `6.3` | `source-budget` |
| `quality:Matched Workflow Evaluation` | `6.9` | `workflow-eval` |
| `quality:Product Experience Is A Kernel Projection` | `6.7` | `adopter-conformance` |
| `repository-governance:Lossless Campaign Intent Closure` | `5.2` | `unit-governance` |
| `repository-governance:Exact Work Lane Lifecycle Effects` | `3.1` | `unit-lanes` |
| `repository-governance:Coupling Binding Registry` | `3.4` | `product-boundary` |
| `repository-governance:Standards Adapter Lifecycle` | `3.4` | `product-boundary` |
| `repository-governance:Productized OpenSpec carrier governance` | `4.1` | `openspec` |
| `repository-governance:Productized OpenSpec Substrate` | `4.1` | `openspec` |
| `repository-governance:OpenSpec customization stays official-compatible` | `4.1` | `openspec` |
| `repository-governance:Official OpenSpec goal metadata is lifecycle-compatible` | `4.1` | `openspec` |
| `repository-governance:Positive Native Reference Ownership` | `3.5` | `product-boundary` |
| `repository-governance:Contextual Authority Resolution` | `2.2` | `unit-authority` |
| `repository-governance:Work Lane Coordination Read Model` | `4.2` | `unit-coordination` |
| `repository-governance:Cohort-bound full Work Lane convergence` | `4.5` | `candidate-throughput` |
| `repository-governance:External Retirement Readiness` | `4.6` | `lane-retirement` |
| `repository-governance:Evolution Governance` | `5.5` | `knowledge-evolution` |
| `repository-governance:Work Lane Lifecycle Resolution` | `3.1` | `unit-lanes` |
| `repository-governance:Land readiness is proof-grounded` | `7.1` | `full-proof` |

## Campaign Dependency Graph

The current Change accumulated independent acceptance boundaries. They remain
separate phase outcomes so each can be implemented and proved without conflating
evidence, but they do not become parallel Changes or task ledgers. `tasks.md` is
the sole progress owner and the table below is only its dependency projection.

| Phase outcome | Source tasks | Dependencies | Independent acceptance / verifier |
| --- | --- | --- | --- |
| `accepted-spec-reconciliation` | carrier reconciliation prerequisite | completed foundations | Stable specs state only implemented behavior; historical archive placement has no current authority; official strict validation and architecture tests pass. |
| `portable-reference-boundary` | `3.4`, `3.5` | `accepted-spec-reconciliation` | Positive native ownership covers references and variation classes across code, tests, docs, schemas, templates, fixtures, and projections; product/private/workstation scans pass. |
| `transition-invariant-proof` | `3.6` | `accepted-spec-reconciliation` | Bounded property, mutation, and formal evidence names state space, budget, kill criterion, and unsupported claims for reducers and Git/Lease effects. |
| `openspec-17-cutover` | `4.1`; `6.10` characterization and lifecycle edge cases | `accepted-spec-reconciliation` | One exact `@fission-ai/openspec@1.7.0` executable owns complete-adopter lifecycle semantics; no cache, PATH, global, 1.6, defaultStore, parsing, or prediction fallback remains. |
| `coordination-reconstruction` | `4.2`, `4.3`, `4.4` | `accepted-spec-reconciliation` | Worktree Family, lane, Lease, handoff, takeover, inbox, records, collaboration, and competition reconstruct from Commitment, Git, fresh Facts, and Attestations with vendor-neutral actor identity. |
| `integration-throughput-housekeeping` | `4.5`, `4.6` | `coordination-reconstruction` | Adaptive admission, parallel proof scheduling, and short candidate CAS preserve stable `dev` throughput; each authorized campaign/budget lane has one absorbed or retired receipt. |
| `repository-knowledge-grammar` | `5.1`, `5.3`, `5.4` | `accepted-spec-reconciliation`, `portable-reference-boundary` | Canonical docs, flat newest-first DRs, rules, skills, specs, schemas, records, tests, and modules have strong grammar, narrow semantic names, and no ambiguous catch-all or physical/logic mismatch. |
| `knowledge-evolution` | `5.2`, `5.5`, `5.6` | `repository-knowledge-grammar` | Contradiction, novelty, overlap, taxonomy gaps, incidents, and repeated review findings update the earliest enforceable owner; valuable meaning is absorbed and stale residue retired. |
| `hermetic-quality-toolchain` | `6.1`, `6.2`, `6.4` | `accepted-spec-reconciliation` | One project `.venv`, uv lock, Nox session plane, Hatchling build, native formatters, schema/link checks, hermetic fixtures, and zero-warning/suppression policy own local and hosted quality execution. |
| `forge-projection-homomorphism` | `5.7` | `repository-knowledge-grammar`, `hermetic-quality-toolchain` | GitLab and GitHub preserve one portable policy while retaining native syntax, complete independent CI/CD, issue/review, protected-ref, and distribution behavior. |
| `terminal-compression` | `6.3`, `6.5`, `6.6` | `portable-reference-boundary`, `repository-knowledge-grammar`, `hermetic-quality-toolchain` | Python/global ELOC, branch coverage, architecture, duplication, dependencies, security, Cyclopts-only CLI, and no shim/wrapper/re-export/alias/compatibility residue pass repository-wide. |
| `adopter-product-surfaces` | `6.7`, `6.8` | `openspec-17-cutover`, `coordination-reconstruction`, `hermetic-quality-toolchain` | Python, Node/polyglot, and docs/infra adopters prove offline lifecycle, recovery, install/uninstall, CLI, SDK, subprocess JSON, schemas/conformance, and optional stateless MCP/A2A projections. |
| `workflow-method-evaluation` | `6.9` | `adopter-product-surfaces`, `hermetic-quality-toolchain` | Matched task × treatment × repetition evidence admits only methods, generators, frameworks, or tools that improve completion, token, time, recovery, intent retention, evidence, and terminal ELOC without a second owner. |
| `terminal-local-closeout` | `7.1`, `7.2` | every preceding local outcome | One immutable local HEAD passes complete proof, advances local candidate and protected `dev` by exact CAS, verifies records, and retires all owned lanes. |
| `dual-provider-publication` | `7.3`, `7.4` | `terminal-local-closeout` | Exactly one `proposal/*` sequence proves and publishes the same commit, version, signed tag, SBOM, provenance, and artifact digests independently on GitLab and GitHub. |

### Transition-Invariant Proof Boundary

Task `3.6` proves bounded claims, never general distributed correctness. The
closed-verdict model exhausts the three verdict values, zero-or-one gaps,
zero-or-one warnings, and reducer sequences of length zero through three. The
Lease state machine runs 20 examples of 12 transitions over renew, handoff
offer/accept, and stale-epoch rejection; it requires stable lane identity,
carrier binding, holder/epoch rules, and zero effect on stale CAS. Existing
effect tests provide concrete witnesses for exact Git multi-ref candidate CAS,
handoff package integrity, retirement compensation after ref failure, and
recovery after Attestation persistence failure.

Mutation scope is exactly `src/ethos/contracts/verdict.py`, selected because it
is deterministic and authority-bearing. `mutmut` runs the bounded verdict tests
with one worker; all authorization-changing mutants must be killed. A survivor
is admissible only when its diff changes no return value, exception type,
mutation effect, or authorization decision; timeout, infrastructure error, or
unclassified survivor is unknown and blocks. The pilot kill criterion is every
semantic mutant killed, not a repository-wide percentage. Unsupported claims
include arbitrary concurrency schedules, filesystem or SQLite failure modes not
injected by the concrete tests, cross-host transport liveness, and takeover
behavior that task `4.4` has not yet implemented.

The final pinned pilot generated 112 mutants and killed 106. The six survivors
were judged equivalent: three alter only the spelling of the missing-severity
default passed to `str`, and three alter only non-authorizing placeholder text
whose presence, not content, closes the verdict. No timeout, infrastructure
failure, suspicious result, or unclassified survivor remained.

Task `3.4` is split truthfully: `7cda1c1c` proves deletion of the coupling and
standards registries plus native-owner derivation for current declared
references; the unproved cross-surface variation-axis remainder stays open in
tasks `3.4` and `3.5`. No unchecked task has an implementation claim.

The graph is acyclic by construction. It orders acceptance work but cannot set
completion, create lifecycle authority, or substitute for checked tasks.

## Alternatives Considered

| Alternative | Decision | Reason |
| --- | --- | --- |
| Rename legacy concepts in place | Rejected | Labels do not remove parallel authority or historical re-evaluation. |
| Shape the semantic kernel with OpenSpec types | Rejected | The kernel remains vendor-neutral while complete mutation-capable adoption deliberately standardizes on OpenSpec. |
| Force every adopter onto built-in `spec-driven` | Rejected | OpenSpec 1.7 natively resolves project-local schemas and arbitrary artifact DAGs; fixing four artifact names discards official capability and blocks valid community workflows. |
| Vendor a large community workflow unchanged | Rejected | Community schemas demonstrate useful patterns, but prompt-only gates, external skill dependencies, persistent duplicate artifacts, and ignored extension keys require independent verification and selective absorption. |
| Replace the greenfield default before a deletion proof | Rejected | Current community sampling validates customization breadth but does not show that an ETHOS-specific schema deletes more code than it adds. Existing custom config is preserved; `spec-driven` remains only the bootstrap default, not a runtime assumption. |
| Resolve mutation workflow from an untracked user-global schema | Rejected | OpenSpec supports global overrides for authoring convenience, but a complete adopter must reproduce the effective artifact graph from the pinned package or repository bytes on another machine. |
| Use one maximal schema for every Change | Rejected | Defects, refactors, features, research, releases, and runbooks need different irreducible artifacts; per-Change schema selection avoids both missing intent and permanent ceremony. |
| Keep a global authority order | Rejected | Different subjects and planes require simultaneous local authorities. |
| Retain amendment and ledger chains | Rejected | They create mutable semantic roots and an additional currentness system. |
| Add a framework for coordination | Rejected | No proved consumer yet justifies its semantic and maintenance cost. |
| Embed COMET Native or Classic | Rejected | It duplicates OpenSpec lifecycle, hook, state, archive, and task authority; only measured external treatment or verified operator output is admissible. |
| Add OpenSpec MCP as a semantic owner | Rejected | OpenSpec 1.7 ships CLI, artifact graph, schemas, and generated Skills but no merged official MCP server; an optional stateless ETHOS MCP may project the same command JSON later without owning files or lifecycle. |
| Add Spec Kit, LID, AIM, ANSS, or another SDD runtime | Rejected | Each would introduce overlapping spec, task, constitution, binding, or workflow authority. ETHOS instead evaluates and may absorb their ambiguity audit, EARS-like patterns, typed derived edges, realization-drift checks, negative scope, and cross-artifact analysis into OpenSpec-compatible owners. |

## Authorized Lane Disposition

Task `4.6` treats lane retirement as semantic garbage collection, not history
merging. Exact Git refs, worktrees, and legacy Lease rows are deleted only after
their independent meaning has a current owner or has been rejected as a lower
implementation of a terminal decision.

| Lane family | Disposition | Terminal owner / reason |
| --- | --- | --- |
| `budget-contract-v2-changed-scope-source-admission-successor-{2..6}` | retired | Direct repository-wide measurement, `domain/source_budget`, tasks `F.1`, `F.10`, `F.12`, and DR-0008 replace the old multi-package changed-scope control plane. Replaying it would restore duplicate package, archive, evidence, and admission owners. |
| `lifecycle-mutation-cli`, its `codex/*` fork, and `campaign-publication-default` | retired | Their committed heads are already ancestors of terminal convergence; no independent bytes or semantics remain. |
| `pytest-cov-subprocess` work/fork refs | retired | `patch = subprocess` and its architecture assertion were independently absorbed by `aeca4514d`; the historical two-line branch adds no owner. |
| `native-lane-resolution-authority-successor-2` committed history | retired | All fifty commits are patch-equivalent to current history; exact Git/Lease/worktree effects now belong to the task `3.3` adapter boundary. |
| `native-lane-resolution-authority-successor-2` uncommitted execution-alias interpreter | rejected after exact preservation | The 200408-byte patch (`sha256:4bb504647f3cad60ef4a3b3a88e4b47526ed4543abd018328a32bd9874322095`) revives the deleted `coupling` runtime under the retired `packages/ethos` tree, duplicates positive native reference ownership, and adds a large replay/state interpreter. Its Git-payload safety intent is already owned by isolated Git adapters and exact effect tests; its ownerless-preservation carrier is historical. The exact patch is retained outside repository truth only until this retirement completes. |

The resulting live topology is intentionally minimal: accepted `dev`, local
`candidate/dev`, and the current terminal-convergence Work Lane. Historical
branch names, compatibility readers, preservation runtimes, or a parallel lane
ledger are not retained.
| Replace OpenSpec with SpecD | Rejected for the current product | SpecD's compiled context, spec/code impact graph, mandatory conformance pass, and multi-workspace model are strong mechanisms, but its young lifecycle, schema, hooks, skills, plugins, archive, and future MCP would replace the selected SDD owner rather than complement it. Re-evaluate only as a measured destructive migration, never a second runtime. |
| Embed Spec Kit, AI-DLC, Agent OS, BMAD, or Kiro workflows | Rejected | Their constitutions, phases, plans, tasks, roles, hooks, or agent state overlap OpenSpec and ETHOS. Absorb only bounded mechanisms such as clarification, cross-artifact analysis, requirement checklists, adaptive depth, explicit decision context, and pre-implementation verification questions. |
| Treat generated Skills or slash commands as task authority | Rejected | Official OpenSpec templates generate host projections from one workflow; they remain replaceable instructions whose drift is checked against the pinned CLI and schema. |
| Delete all history | Rejected | Immutable bytes may be needed for recovery and audit, but not as current truth. |
| Replace tasks wholesale after redesign | Rejected | It destroys progress identity, hides dropped obligations, and permits old decisions to reappear. |
| Preserve every conversation sentence as a repository ledger | Rejected | Raw dialogue is context; accepted independent obligations belong in their semantic owners and verifiable tasks. |
| Finish phases without independent acceptance boundaries | Rejected | It repeats the non-convergence failure by conflating unrelated evidence. |
| Add a Campaign manifest or task ledger | Rejected | This Change and `tasks.md` already own lifecycle and progress truth. |
| Create successor Changes for current phases | Rejected | It duplicates progress authority and recreates lane and carrier explosion. |

## Migration Risks

- **Carrier/model cutover can change digests.** Bind leases and effects to exact
  carrier bytes/tree digests and perform one explicit CAS bootstrap; do not
  retain dual evaluators or dual readers.
- **Deletion can lose unique meaning.** Inventory independent semantic deltas
  before deletion; preserve history where required and prove no active consumer.
- **OpenSpec drift can split the Change lifecycle.** Pin and characterize 1.7
  for every complete adopter; observation-only repositories fail closed before mutation.
- **Parallel work can race.** Use exact scopes, fresh facts, resource leases,
  and short CAS integration; never infer ownership from visibility.
- **Projection drift can conceal inconsistency.** Require declared source
  bindings and generated/diff checks at the earliest feasible gate.
- **Long-running activity can conceal non-convergence.** Keep one ordered
  critical path, require a verified terminal-state delta at every phase exit,
  and move independent review off the mutation path.

## Migration Sequence

1. Restore the pre-cutover kernel-test and carrier-classification tasks under
   their original identifiers, close accepted feedback without resetting stable
   task identity, and finish the current OpenSpec replica-deletion slice.
2. Cut Commitment, Attestation, Facts, TransitionPlan, verdict, and digest
   semantics; delete amendment and closed-kind paths.
3. Replace authority rank/currentness/legacy replay with contextual resolver,
   five-role extraction, model-gap handling, and byte/tree-bound lease cutover.
4. Complete tasks `3.3` through `3.6` in dependency order and prove the phase
   exit before entering product-profile and coordination work.
5. Continue tasks `4.x` through `6.x` in the same Change, using each phase outcome
   as an atomic local checkpoint without creating another progress carrier.
6. After every local obligation closes, archive this Change once, run terminal
   local closeout, and perform one dual-provider publication sequence on the
   resulting immutable HEAD.
