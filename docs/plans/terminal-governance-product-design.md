---
subject: ethos:terminal-governance-product-design
role: plan
state: canonical
relations:
  canonical_for: terminal product architecture and terminal-convergence campaign
---

Status: canonical product design; implementation is tracked by the active
`terminal-convergence` OpenSpec change.

Purpose: define ETHOS's smallest vendor-neutral semantic kernel, product boundary, and
terminal transition model.

See also: [Product Design Contract](../governance/product-design-contract.md) and
[Terminal Convergence](../../openspec/changes/terminal-convergence/proposal.md).

# Terminal Governance Product Design

## Terminal Claim

ETHOS is a Git-native, local-first, vendor-neutral trustworthy change compiler.
It turns intent into the shortest provable repository state transition:

```text
intent -> contract -> facts -> plan -> proof -> effect -> attestation
```

Its unique value is not another workflow engine. ETHOS makes repository change
deterministic, authority-bounded, recoverable, evidence-bearing, and portable
across humans, agents, tools, repositories, and forge providers.

The public lifecycle is:

```text
status -> plan -> prove -> land -> publish
```

Setup and explanation remain separate:

```text
inspect  adopt  doctor  explain
```

`orient` folds into `status`. `report` is removed. Facts, gaps, evidence, and
next actions replace scores and self-awarded readiness.

## Root Constraints

1. Truth precedes convenience. Missing or stale evidence never becomes pass.
2. Less is more only when meaning, safety, and product capability survive.
3. Open-world facts feed closed-world transitions.
4. Git and declared contracts are truth; caches, sessions, indexes, and views
   are replaceable projections.
5. One semantic obligation has one owner. No shim, re-export, alias, wrapper,
   thin forwarder, or parallel implementation survives without unique meaning.
6. Prefer mature native capability when it reduces total maintenance cost.
7. Destructive migration is the default. Compatibility exists only when a
   current user instruction explicitly requires it.
8. Local use, validation, installation, and recovery do not depend on a forge.
9. Provider, language, repository layout, and agent vendor are adapter facts,
   never kernel vocabulary.
10. A hard gap cannot be averaged away by a score, warning, or advisory.

## Product Boundary

ETHOS owns:

- intent preservation and executable change contracts;
- repository fact observation and authority classification;
- deterministic planning, proof selection, effect admission, and attestation;
- Worktree Family coordination, recovery, integration, and publication;
- adopter profiles, conformance, and bounded extension protocols.

ETHOS does not become:

- a generic issue tracker, agent runtime, DI container, event bus, scheduler,
  workflow SaaS, graph database, policy server, or long-running job engine;
- a replacement for Git, OpenSpec, CI, package managers, or forge-native
  releases;
- a universal physical repository layout;
- a compatibility museum for previous ETHOS designs;
- a product coupled to any workstation-specific control plane.

## Minimal Semantic Kernel

Only two persistent semantic entity types exist.

### `ChangeContract`

An immutable contract for one intended repository transition. It contains:

- intent, subject, scope, invariants, acceptance, risks, authority, permissions;
- hypotheses, experiment strategy, dependencies, campaign membership;
- collaboration strategy, compatibility stance, and publication boundary.

Intent amendments are `Attestation` records folded over the immutable base
contract. Chat history and a live agent session are never required to recover
the effective intent.

### `Attestation`

An immutable statement bound to issuer, subject, time, content digest, and
evidence references. It subsumes evidence receipts, claims, decisions,
transitions, reviews, handoffs, recovery, experiments, evaluations, and release
provenance. An attestation records an observation or judgment; it never creates
authority by itself.

Everything else is derived or transient:

- `RepositoryFacts`: freshly observed Git, filesystem, config, tool, provider,
  and attestation facts;
- `PlanIR`: deterministic, hashable, replayable DAG nodes of `Check`, `Decision`,
  and `Effect`;
- Chronicle, knowledge graph, shared inbox, dashboards, reports, search indexes,
  state-machine views, and metrics: projections over the two entities and
  current facts.

This model absorbs ontology, knowledge graph, finite-state-machine, DAG,
persistent execution, hypothesis, feedback, and collaboration needs without
creating separate truth stores.

## Transition Semantics

The verdict algebra is closed:

```text
pass | block | unknown
```

Advisories are separate. `unknown` means the verifier cannot currently prove a
required proposition; it is not a weak pass.

Each PlanIR node is pure data:

| Node | Duty |
| --- | --- |
| `Check` | Observe or verify a proposition without mutation. |
| `Decision` | Apply a declared rule to facts and prior node results. |
| `Effect` | Describe one idempotent, permission-bounded mutation with CAS preconditions. |

`graphlib.TopologicalSorter` is the sole in-process DAG ordering mechanism.
No `GraphKernel`, `ActionGraph`, `WorkflowGraph`, or graph framework wrapper
remains. Rich graph analytics, if ever required, are an optional projection.

Effects execute only when the compiled plan hash, repository facts, authority,
lease generation, expected HEAD, and permissions still match. Execution emits
an attestation. Replay skips an already-attested identical effect and blocks a
same-identity/different-content collision.

## Declarative, Functional Implementation

The implementation center is pure transformation:

```text
observe(root) -> RepositoryFacts
compile(ChangeContract, RepositoryFacts) -> PlanIR
judge(PlanIR, attestations) -> verdict
execute(admitted Effect) -> Attestation
```

I/O is confined to composition roots and explicit adapters. Domain reducers are
total where practical, immutable by default, and return values rather than
mutating hidden state.

Terminal choices are singular:

| Concern | Terminal choice | Rejected residue |
| --- | --- | --- |
| Persisted/external contracts | Pydantic v2, strict and frozen | attrs/dataclass/Pydantic dual models |
| Temporary internal values | tuples, mappings, enums, small frozen stdlib values | a second model framework |
| CLI | Cyclopts declarations as command SSOT | argparse and parallel registries |
| DAG | direct `graphlib.TopologicalSorter` | custom graph layers, NetworkX core dependency |
| Guard DSL | CEL through official `cel-expr-python` after parity bake-off | celpy dual-run, CUE/Rego/Cedar core |
| Dependency composition | explicit constructor/function arguments and Protocols | DI container or service locator |
| Events | returned attestations and external streams | in-process event bus |
| State transitions | declarative PlanIR plus pure reducers | state-machine framework |
| Long execution | resumable plans plus attestations | Temporal, DBOS, Restate core dependency |
| Extension discovery | manifests, subprocess JSON, then stdlib entry points | pluggy before real consumers |
| Text scaffolds | optional Copier/Jinja scaffold packs | Jinja in core or empty template machinery |

Code generation is admitted only when a schema is the SSOT, generated output is
never hand-edited, drift is checked, and generated ELOC remains measured. It is
used for protocol bindings, schemas, and optional adopter scaffolds, not to hide
product complexity.

## Command And Data Surfaces

Default JSON is bounded and stable. It carries only verdict, summary, required
gaps, next actions, and references to larger artifacts.

| Surface | Maximum default payload |
| --- | ---: |
| `status` | 16 KiB |
| `plan` | 32 KiB |
| one attestation | 64 KiB excluding referenced artifacts |

Verbose diagnostic data is written to an artifact and referenced by digest.
No default command emits a multi-megabyte repository dump.

Cyclopts declarations own command names, parameters, help, and dispatch. SDK,
MCP, docs, shell completion, and schemas are generated or validated against
that declaration rather than maintained as command-shaped copies.

## Self/Adopter Homomorphism

The universal kernel knows no OpenSpec, Python, GitHub, GitLab, Codex, Claude,
JetBrains or fixed directory grammar. An adoption profile maps native
repository facts into kernel roles:

- change carrier and intent source;
- branch roles and publication destinations;
- gate providers and effect executors;
- documentation, formatting, package, release, and evidence conventions;
- optional organization policy and extension packs.

The ETHOS self profile chooses OpenSpec, Repository-Family governance, strict
branch roles, and the repository's current quality floor. Adopters may choose
different native carriers and layouts while preserving command semantics and
attestation protocol.

OpenSpec is mandatory for ETHOS itself and optional for adopters. Physical
Repository-Family paths are a self-profile best practice, not universal kernel
law.

## Worktree Family And Intent Continuity

One `ChangeContract` derives one Worktree Family. The family is a Git/resource
projection, not another semantic entity.

A family may contain:

- cooperative slots with disjoint declared scopes;
- at most two competitive variants evaluated against identical acceptance;
- read-only research workers;
- one canonical family head eligible for integration.

Only the canonical head reaches the candidate train. A selection attestation
records why a competitive variant won and which useful intent was absorbed.
Losing variants are retired after preservation evidence exists.

The shared inbox is a projection of unconsumed intent amendments, decisions,
handoff offers, conflicts, and evidence gaps. Agents coordinate before work when
scope overlap is known; competition is admitted only when alternative designs
have information value greater than duplicate cost.

Every handoff/takeover package is reproducible from:

```text
ChangeContract + amendments + exact HEAD/tree + diff + RepositoryFacts
+ open PlanIR nodes + attestations + lease generation + next admissible action
```

It excludes transcript dumps and vendor session formats. Takeover uses CAS,
quiescence evidence when available, and an explicit unknown boundary when the
source session is lost. Orphaned lanes are detected, preserved, absorbed,
superseded, or retired through native lifecycle commands; direct ref/worktree/
SQLite deletion is forbidden.

## Concurrency And Integration Train

There is no global WIP limit of three. Backpressure is adaptive and based on:

- overlap/conflict graph density;
- host CPU, memory, disk, and agent capacity;
- proof latency and candidate queue age;
- candidate train throughput and retry rate;
- handoff completeness and recovery cost.

Authoring is wide, proof is parallel, and the final candidate update is a short
serialized compare-and-swap operation. A stale candidate observation causes
rebase/reproof, never an overwrite. Queue scheduling favors high-impact,
low-conflict, old, fully-proven changes without starving urgent fixes.

Campaign iterations run local closeout only. Remote CI and publication run once
after the campaign's terminal acceptance is satisfied.

## Branch And Publication Topology

ETHOS self profile:

| Branch | Meaning | Remote policy |
| --- | --- | --- |
| `main` | protected default release branch | GitLab and GitHub |
| `dev` | protected stable integration branch | GitLab and GitHub |
| `candidate/dev` | local integration train | never pushed |
| `work/*` | local authoring lanes | never pushed |
| `proposal/*` | remote review and delivery | GitLab and/or GitHub |

`proposal/*` replaces `submit/*` and provider-specific `pr/*`: it describes the
repository semantic role, not a forge UI mechanism.

Three independent planes exist:

1. Local validation and installation, with no remote dependency.
2. GitLab as the organization publication source.
3. GitHub as an independent full repository, CI/CD, release, update, and
   distribution plane.

The final immutable commit is proposed to both providers. Each provider emits
its own CI and release attestations. The same signed tag and artifact digests
must be observed on both; one provider's success never proves the other.

## Records, Evidence, And Recovery

For the ETHOS self profile, immutable record directories follow Repository-
Family governance. Record payloads are attestations plus referenced artifacts,
with `README.md`, `closeout.json`, `MANIFEST.json`, and `SHA256SUMS` as integrity
carriers. Historical records are indexed and superseded, never rewritten to fit
a newer schema.

Tracked truth contains durable contracts and attestations. Ignored SQLite,
indexes, caches, proof workspaces, and generated views are rebuildable. Their
retention and GC are governed operations; ignored does not mean disposable.

## Documentation And Physical Form

The repository uses one form per semantic class:

| Class | Canonical form |
| --- | --- |
| human judgment and rationale | Markdown with fixed front matter and section grammar |
| owned configuration and routing | TOML |
| public machine payload and standards | JSON/JSON Schema |
| ecosystem-native configuration | YAML only when the ecosystem owns it |
| generated streams | ignored JSONL |
| local index/cache | ignored SQLite |

Entrypoints link; they do not restate. Rules are concise executable obligations.
Design lives in canonical docs. OpenSpec carries active change intent and deltas.
Attestations carry proof and decisions. Archives use the sole name grammar
`YYYY-MM-DD-<kebab-id>`.

Whitespace is tool-owned: LF, UTF-8, final newline, no trailing whitespace, and
no repeated blank lines in Markdown/config. Ruff owns Python vertical spacing;
dprint owns JSON/TOML/YAML; rumdl owns Markdown; shfmt owns shell. Manual
format-disable regions are terminally forbidden in production source.

## Quality And Supply Chain

One owner exists for every quality property:

| Property | Owner |
| --- | --- |
| Python lint and format | Ruff |
| Python types | Pyright strict |
| Markdown | rumdl |
| JSON/TOML/YAML format | dprint |
| shell format/lint | shfmt and ShellCheck |
| structural policy | ast-grep |
| import boundaries | import-linter |
| lifecycle/concurrency properties | Hypothesis state machines plus Quint models |
| mutation testing | mutmut for pure critical reducers only |
| source measurement | scc plus canonical formatting and Python AST/tokenize |
| duplicate investigation | AST-aware duplicate tools as advisory, never competing truth |
| SBOM | Syft to SPDX |
| provenance | in-toto Statement plus DSSE, aligned with SLSA |
| CI binary supply | Aqua |
| version coordination | bump-my-version |
| local GitHub workflow replay | act, where runner semantics permit |

Warnings are errors in local, build, test, provider CI, packaging, docs, and
deprecation output. Production `fmt off`, `fmt skip`, `noqa`, and type-ignore
suppressions reach zero. Global branch coverage is at least 95%; authority,
CAS, and transition reducers are 100%. Tests that exist only to touch branches
are deleted. Mutants in critical pure reducers must be killed or explicitly
classified with evidence.

## Budget And Anti-Gaming Mechanism

Campaign budget is a vector, not a vanity ELOC score:

- Python ELOC at terminal state: at most 54,000;
- global owned-source ELOC at terminal state: at most 68,000;
- default output payload bounds above;
- zero warnings and inline suppressions;
- coverage and mutation floors;
- no duplicated command, schema, policy, graph, or lifecycle owner;
- bounded proof latency and dependency surface.

ELOC excludes comments, blank lines, and docstrings, but includes product,
tests, tools, scripts, templates, generated owned source, and executable config.
Moving logic from Python into config, templates, generated code, tests, or tools
does not earn deletion credit.

Intermediate growth is allowed when it shortens the terminal path. Per-change
net-negative gates are advisory inside this campaign; terminal budgets are hard.
A budget gap forces `block` and can never coexist with `ok=true`, publish-ready,
closed-loop, or a perfect score.

Capability preservation, contract scenarios, mutation testing, and adopter
conformance prevent agents from gaming ELOC by deleting behavior or assertions.
Current-HEAD attestations prevent stale proof and hallucinated completion.
Independent provider attestations and CAS prevent self-awarded publication.

## Security And Authority

Actor references are vendor-neutral opaque identifiers with the structural form
`kind:namespace:instance-kind:id`. The kernel validates shape and equality only;
it never enumerates vendors or infers privilege from a namespace.

Capabilities are explicit, least-privilege, path- and effect-scoped, time-bound,
and rechecked immediately before mutation. Secrets, credentials, private
sessions, and full request bodies never enter contracts, attestations, records,
or handoff packages.

## Ecosystem

The ecosystem begins only after kernel and conformance stability. Language-
neutral schemas define ChangeContract, PlanIR, Attestation, adapter manifests,
permissions, and pack protocols.

Admitted pack types are:

- fact provider;
- change carrier;
- gate provider;
- effect executor;
- attestation sink;
- projection;
- scaffold.

The Conformance Kit proves determinism, authority isolation, permission bounds,
offline behavior, uninstall cleanliness, and protocol compatibility. Packs use
data or subprocess JSON first; trusted in-process entry points come later only
with real consumers.

MCP exposes resources, prompts, and guarded tools. A2A handles discovery,
delegation, handoff, and takeover. Catalogs are federated rather than requiring
a central marketplace. Optional fleet dashboards, hosted proof runners,
attestation indexes, organization policy distribution, and cross-repository
campaigns remain outside the local kernel.

## Concern And Capability Preservation Matrix

| Concern | Terminal carrier/mechanism | Acceptance proof |
| --- | --- | --- |
| Product identity and unique value | this design and product contract | command and adopter conformance |
| Less-is-more without semantic loss | two entities plus preservation matrix | terminal ELOC and all scenarios green |
| SSOT/DRY/MECE/SOLID | one owner per obligation and import rules | ast-grep/import-linter/duplicate audit |
| Declarative/functional/low-code | PlanIR, CEL, pure reducers, generated projections | determinism and replay tests |
| Graph/DAG/FSM/ontology/KG | graphlib plus derived projections | cycle/order/property tests |
| Persistent execution and recovery | effect identity plus attestations | crash/retry/idempotency tests |
| Feedback, hypothesis, research, experiment | contract fields plus attestations | hypothesis lifecycle scenarios |
| Formal reasoning and invariants | Quint plus Hypothesis | model and state-machine gates |
| Intent recognition/confirmation | immutable contract plus amendments | effective-intent fold tests |
| Shared inbox/A2A/agent collaboration | derived inbox and protocol adapters | handoff/takeover conformance |
| Cooperative and competitive work | Worktree Family with <=2 variants | selection/absorption/retirement receipts |
| Lane loss and session damage | vendor-neutral recovery package | cold takeover without transcript |
| Lane explosion | adaptive admission and family canonical head | orphan/queue/backpressure metrics |
| Candidate throughput/races | parallel proof plus serialized CAS | contention and stale-head tests |
| Worktree Family and records | self-profile projections and attestations | repo-family audit and record verify |
| Vendor neutrality | opaque actor refs and adapter profiles | three unlike reference adopters |
| Workstation-control-plane independence | zero active dependencies | repository-wide zero-coupling scan |
| Local/GitLab/GitHub separation | three authority planes | independent immutable receipts |
| Branch semantics | main/dev/candidate/work/proposal roles | policy and remote-ref tests |
| OpenSpec shape/archive naming | self-profile carrier and one grammar | official strict validation and archive audit |
| Documentation form and whitespace | carrier grammar and native formatters | docs/config quality gates |
| CLI and output economy | Cyclopts SSOT and artifact references | surface snapshot and payload caps |
| Quality tools and warnings | single-owner tool stack | zero-warning complete proof |
| Code generation/scaffolding | schema generation and optional Copier/Jinja pack | drift and uninstall tests |
| Supply chain | Aqua, Syft, SPDX, DSSE, SLSA | signed SBOM/provenance attestations |
| Token and change latency | compact views, direct next action, selective context | byte, step, latency, and token budgets |
| Anti-gaming and hallucination | hard verdicts, current-HEAD attestations, independent proof | adversarial false-green suite |
| Product ecology | protocols, TCK, packs, MCP/A2A | external pack and adopter conformance |

## Terminal Acceptance

The campaign is complete only when all are true:

1. `status`, `plan`, `prove`, `land`, and `publish` share one verdict algebra and
   cannot emit a green state with a hard gap.
2. `report`, standalone `orient`, parallel command registries, custom graph
   layers, source-budget worker/protocol/replay/shadow stacks, empty template
   machinery, workstation-control-plane coupling, and compatibility residue are absent.
3. ChangeContract, Attestation, RepositoryFacts, and PlanIR own the semantic
   center; old package/model/schema owners are deleted in the same cutover.
4. Python ELOC is <=54,000 and global owned-source ELOC is <=68,000.
5. Warnings and production suppressions are zero; quality, coverage, mutation,
   concurrency, source, docs, shell, config, and supply-chain gates pass.
6. Python package, Node/polyglot, and docs/infra adopters complete inspect,
   adopt, status, plan, prove, land, publish, handoff, recovery, and offline
   install without Python layout or OpenSpec assumptions.
7. Local, GitLab, and GitHub receipts remain distinct and bind the same final
   commit, signed tag, and artifact digests.
8. All campaign Worktree Families are absorbed or retired through native
   lifecycle commands and immutable records verify.

## Shortest Landing Route

One campaign, deletion first, no repeated remote closeout:

1. **Restore truth**: fix false-green verdicts, bound outputs, bind concern
   coverage, and classify existing Work Lanes.
2. **Delete self-defeating surfaces**: source-budget private runtime, empty
   templates, copied CI/C4/config parsers, command/schema dual truth, external
   workstation coupling,
   compatibility paths, and coverage-only tests.
3. **Cut over the semantic kernel**: introduce the four minimal runtime values,
   direct graphlib, official CEL, and one distribution; delete old owners at the
   cutover commit.
4. **Cut over lifecycle and train**: one reducer, explicit Git adapter, Worktree
   Family, amendments, handoff/takeover, adaptive backpressure, CAS candidate,
   and `proposal/*`.
5. **Cut over quality and supply chain**: singular format/lint/type/test,
   warnings-as-errors, suppression zero, SBOM, provenance, binary supply, and
   versioning.
6. **Prove homomorphism**: three reference adopters and offline lifecycle.
7. **Expose the minimum ecosystem**: schemas, TCK, manifests, permissions,
   subprocess/data packs, MCP/A2A, optional scaffold pack.
8. **Close once**: complete local proof, create one final proposal, run both
   provider planes, fast-forward `dev` then release `main`, verify immutable
   artifacts, retire all families, and verify records.

No later stage may preserve an earlier implementation merely to reduce cutover
risk. The shortest safe path is replacement followed immediately by deletion.
