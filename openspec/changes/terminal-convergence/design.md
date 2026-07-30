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
   universal manifest, registry, ledger, or index is persisted.
3. **Contextual authority.** Authority/currentness resolves per subject,
   predicate, scope, plane, validity, and context. Global rank, timestamp-only
   selection, `CURRENT`, accepted/superseded directory status, and manual
   indexes are deleted as authority devices. Ambiguity blocks; valid novelty is
   `model_gap`.
4. **One generic transition mechanism.** Observe, extract, resolve, compile,
   evaluate, exact CAS apply, post-observe, attest, then project. Command
   sequences, archive actions, campaign displays, lane phases, and provider
   pipelines are profile projections; no fixed lifecycle is embedded in the
   kernel.
5. **Effects close through exact bindings.** A TransitionPlan contains exact
   commitment, fact, prior-attestation, policy, and effect bindings. The adapter
   rechecks preconditions at CAS time. Post-observation and an Attestation—not
   a replayed historical workflow—establish what occurred.
6. **The kernel is neutral; complete adoption is opinionated.** Commitment,
   Facts, TransitionPlan, and Attestation remain independent of OpenSpec types,
   while every mutation-capable adopter pins verified OpenSpec as the sole
   Change, design, spec, task-progress, dependency, and archive carrier.
   Observation-only repositories may omit it but cannot enter governed mutation.
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
   conformance evidence, uninstall cleanliness, and net deletion.
10. **One quality owner per property.** Local and hosted execution consume the
    same declarations. Warnings, suppressions, unknown required facts, and
    projection drift fail closed. JSON receives schema validation and canonical
    serialization from its declared owner, not an invented formatter.
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
| `docs/decisions/**`, `docs/plans/**` | Decision records and plans | deleted-after-proof | flat DR metadata, Git history, and current OpenSpec tasks | `5.4`, `5.6` | DR grammar and absorptive retirement prove no parallel ledger |
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
Spec Kit is not a core dependency and COMET remains only such a candidate.

The owner-native archive is the final tracked source mutation, not the final
proof claim. It changes HEAD, so local proof, proposal/hosted verification, and
dual-provider publication execute once on the post-archive commit. The archived
task bodies preserve execution history only; accepted capability specs and fresh
Facts recompile the Phase 7 effects, whose completion is stated only by HEAD-bound
Attestations and receipts. Archived history is neither authority nor a progress
store.

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
| Retired Subject/Contract/Transition/Inscription/Chronicle/Evolve vocabulary does not define the terminal kernel | superseded | Commitment, Facts, TransitionPlan, Attestation, and model promotion; `1.1` through `3.2` | kernel contract, authority, and lifecycle tests |

## Accepted Feedback Closure

The superseded conversation ledger is reduced here into current semantic
owners. `deferred` means a concrete consumer must first satisfy task `6.9`;
`superseded` means a later explicit terminal decision replaced the old shape
without dropping its underlying concern.

| Feedback | Disposition | Current tasks | Current semantic owner or reason | Verifier |
| --- | --- | --- | --- | --- |
| CL-001 | superseded | `5.3` | one `src/ethos` distribution with narrow semantic modules replaces package-count design | module-boundary and import-linter gates |
| CL-002 | absorbed | `5.5`, `6.7` | skill quality and adopter proof | skill portfolio and adopter gates |
| CL-003 | absorbed | `5.5` | skill activation remains a repository registry, never provider metadata | skill schema and projection-drift gates |
| CL-004 | absorbed | `F.7`, `5.5` | Superpowers remains an optional observable method pack | method-pack authority architecture test |
| CL-005 | deferred | `4.4`, `6.9` | host capabilities are optional facts or adapters and never repository truth | profile/adopter conformance |
| CL-006 | deferred | `6.9` | backlog intake requires a real adopter proving unique need and net deletion | adapter admission and uninstall proof |
| CL-007 | absorbed | `6.7` | adoption classifies native tool surfaces without productizing adopter vocabulary | three-adopter adoption reports |
| CL-008 | superseded | `F.9`, `4.1`, `6.10` | official OpenSpec owns the complete adopter Change lifecycle; ETHOS owns admission, proof, and effects | official strict validation and lifecycle tests |
| CL-009 | absorbed | `5.5` | capability coverage, overlap, novelty, and retirement checks evolve the taxonomy | spec coverage and overlap gates |
| CL-010 | superseded | `2.1`, `3.2`, `5.2` | open predicates, model promotion, and Attestations replace an evolution ledger runtime | model-gap and Attestation tests |
| CL-011 | absorbed | `3.1`, `6.1` | one TransitionPlan compiler and declared gate owners | plan determinism and gate execution tests |
| CL-012 | absorbed | `6.1`, `6.4` | native format, artifact, evidence, and projection owners | full quality proof |
| CL-013 | absorbed | `6.7` | three profile-bound reference adopter shapes | adopter conformance suite |
| CL-014 | absorbed | `6.7`, `6.8` | portable contracts and profiles keep domain semantics outside the product | profile isolation and schema conformance |
| CL-015 | absorbed | `7.1`, `7.2`, `7.3`, `7.4` | local, protected-ref, hosted, and publication proof remain separate planes | terminal closeout receipts |
| CL-016 | absorbed | `7.4` | each provider verifies its own hosted signature and release facts | GitLab and GitHub release observations |
| CL-017 | absorbed | `6.6` | repository hygiene forbids `.mailmap` unless a future explicit design changes the owner | repository hygiene architecture test |
| CL-018 | rejected | `6.9` | history rewrite is not a standing product mechanism; any migration requires a separately admitted consumer | product-boundary gate |
| CL-019 | absorbed | `5.1`, `5.4` | canonical information architecture and flat DR grammar | docs registry, links, and DR grammar |
| CL-020 | superseded | `6.7` | strict profiles bind native repositories without full-skeleton generation | profile round-trip and conflict tests |
| CL-021 | absorbed | `6.7`, `7.4` | Node/polyglot adopter and dual-provider artifact proof own npm distribution quality | npm pack, install, and publication receipts |
| CL-022 | absorbed | `F.5` | the six Cyclopts roots are the sole public command plane | live Cyclopts architecture test |
| CL-023 | absorbed | `7.3`, `7.4` | hosted results enter as plane-bound Attestations, never a second truth store | independent provider Attestations |
| CL-024 | absorbed | `6.1`, `6.9` | standards have one admitted owner, bounded evidence, exit strategy, and consumer | tool admission and dependency gates |
| CL-025 | superseded | `0.4`, `0.5` | structural history and intent checks replace a permanent conversation ledger | intent-closure architecture test |

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
| `4.1` | `b7918d4d35027a9193c1b5424b1abfe58ddd11f44fa824b2c751782cfa942e7c` | `b301e40fa59dc5bd192d169f033515d9879e78ec8d1a50a17dceca1884c5a3da` | clarified | OpenSpec 1.7 characterization, nested specs, artifact dependencies, and removal of the 1.6 reader became explicit acceptance obligations. |
| `6.10` | `9fe10d07717cf56b5696e8e4fc0ed91737e060de10e8e89121f78ba01a0d49c6` | `6dfc3d418c1b630624d1281111cf564cc6dc1f605b80ed511fe184c70a8c8905` | clarified | Official 1.7 archive edge cases and fail-closed validation became explicit acceptance obligations. |
| `4.1` | `b301e40fa59dc5bd192d169f033515d9879e78ec8d1a50a17dceca1884c5a3da` | `3c12cf104f3867dbe7e926b9622390117c81b008cc496bc693ab73eae817e64f` | superseded | The later product ruling keeps the kernel vendor-neutral but requires verified OpenSpec for every mutation-capable complete adopter. |
| `5.5` | `2dc34a5e4de059a8618df1f59425c54274d72774235e8aa7f11e27f210238c6b` | `ca758f3eca189fda18b6607775156f998eb4eb1ee67cf556d7a434ceae5d8b0d` | clarified | Official OpenSpec Skills are generated projections and cannot own task or lifecycle authority. |
| `6.1` | `d1af42bbc127276837574e07e7119acf7abe0f5d01f3bfd3c6b36d0be1e2cc0d` | `e27506e17c7d959264d3a94f0e5d92f49fc791ba414d9b42aeb7326143229001` | clarified | Direct dependency floors, immutable non-Python identities, and lock ownership became explicit supply-chain obligations. |
| `6.5` | `69b7dbe3409998637d2c193c19cc5830fdd774829d2ad35340963baeab2a39a0` | `a0877a0bd062cd77cdf546c3f8fe11b220399626382832aa2bdbbdf93ae5213a` | clarified | One online refresh owns latest-stable proposals while normal proof remains offline and lock-bound. |
| `6.7` | `6176a543b092c496d3f098e539fc0e4afb287c77bd507abeaa4295f3fa7192f6` | `9c76a47117bceb83cf2e0490d1d940cb75d4b4d4765f1504a8dd64f3b3517b5e` | superseded | The later adoption ruling limits no-OpenSpec operation to observation-only repositories and requires the full OpenSpec lifecycle for governed mutation. |
| `6.9` | `a17de7104426643874350289628855d3c8b771467669b7ec5b3f6ee155c0034a` | `7144cc607c7c0f178601edc7eb7744565b695b7aede85d4b21733426b7405456` | clarified | Spec Kit is excluded from the core and COMET remains only an external candidate under the existing consumer and net-deletion bar. |
| `6.10` | `6dfc3d418c1b630624d1281111cf564cc6dc1f605b80ed511fe184c70a8c8905` | `4f126e51c7c545b72e4bb02c17847ef5faa25e5b590a7af2389045c392ae72bd` | clarified | The archive receipt must bind the exact effective OpenSpec 1.7 executable and tool version. |

## Alternatives Considered

| Alternative | Decision | Reason |
| --- | --- | --- |
| Rename legacy concepts in place | Rejected | Labels do not remove parallel authority or historical re-evaluation. |
| Shape the semantic kernel with OpenSpec types | Rejected | The kernel remains vendor-neutral while complete mutation-capable adoption deliberately standardizes on OpenSpec. |
| Keep a global authority order | Rejected | Different subjects and planes require simultaneous local authorities. |
| Retain amendment and ledger chains | Rejected | They create mutable semantic roots and an additional currentness system. |
| Add a framework for coordination | Rejected | No proved consumer yet justifies its semantic and maintenance cost. |
| Delete all history | Rejected | Immutable bytes may be needed for recovery and audit, but not as current truth. |
| Replace tasks wholesale after redesign | Rejected | It destroys progress identity, hides dropped obligations, and permits old decisions to reappear. |
| Preserve every conversation sentence as a repository ledger | Rejected | Raw dialogue is context; accepted independent obligations belong in their semantic owners and verifiable tasks. |

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
4. Move fixed lifecycle and OpenSpec-only assumptions into the ETHOS self
   profile; reduce coordination to resource facts plus attested effects.
5. Reclassify and absorb docs, DRs, rules, skills, schemas, CI, records,
   evidence, and OpenSpec material; delete only after semantic proof.
6. Collapse quality/supply-chain tooling, remove warnings/suppressions, prove
   three adopter shapes and portable interfaces, archive as the final source
   mutation, then run one local and one dual-provider campaign closeout on that
   immutable HEAD.
