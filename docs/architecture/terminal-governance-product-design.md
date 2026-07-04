---
subject: ethos:terminal-governance-product-design
role: target-design
state: active
relations:
  canonical_for: destructive terminal redesign target after user authorization
  derives_from: product design conversation, ETHOS current docs, dmgr rules, di-effect Tao
---

# Terminal Governance Product Design

Status: active target design.

Purpose: carry the complete terminal design for a destructive, low-code,
configuration-driven ETHOS redesign so another agent can continue the work
without relying on chat history.

This page is a target design, not a compatibility plan. Current code and docs
remain current facts until changed, but they are not the desired end state when
they conflict with this page.

This lane lands design and planning substrate only. It does not claim the full
terminal runtime, hook system, projection generator, scaffold system, package
collapse, release workflow, or extension runtime is implemented.

## Product Thesis

ETHOS is a repository governance product. Quality is one governed view of the
product, not the product itself.

ETHOS governs one Git repository through one loop:

```text
status -> plan -> prove -> land -> publish
```

The product must answer:

```text
Where am I?
Can I mutate?
What should change?
Which proof is required?
Is evidence sufficient?
Can this land?
Can this publish?
What did we learn?
```

The answer must be small enough for humans to trust and structured enough for
machines to execute. ETHOS therefore separates judgment, contract, method,
instrumentation, and proof.

## Philosophical Kernel

The terminal model uses five layers:

| Layer | Meaning | Repository carrier |
| --- | --- | --- |
| Tao | Aesthetic and value judgment. What is worth preserving, simplifying, or rejecting. | `system/tao.md`, `ETHOS.md` |
| Contract | Machine-checkable obligations and boundaries. | `system/*.toml`, `system/schemas/`, OpenSpec specs |
| Method | Workflows and procedures for safe change. | `system/workflows.toml`, `rules/`, OpenSpec changes |
| Instrumentation | Mature tools used well, or small tools built to fit. | `.config/`, `system/tools.toml`, `extensions/` |
| Proof | Sedimented facts, evidence, and attestations. | `evidence/`, Git refs, attestations |

The writing standard is:

| Standard | Meaning | Consequence |
| --- | --- | --- |
| Trustworthy | No claim without authority or proof. | Evidence and citations bind claims. |
| Expressive | Humans and machines can recover intent. | Markdown for judgment, TOML for durable config, JSON for API output. |
| Elegant | No excess surface. | Delete parallel entities, wrappers, and historical residue. |

## First Principles

1. A repository governance product is useful only when it reduces invalid states.
1. Failure blocking must move upstream. The best gate is the one that makes an
   invalid action impossible before it mutates tracked truth.
1. A truth store that cannot be proved or projected safely is not a truth store.
1. A generated surface is a liability unless drift is checkable.
1. A workflow state stored as mutable private state is weaker than a state
   derived from Git, OpenSpec, evidence, and contracts.
1. A new entity is justified only when it owns a distinct semantic obligation.
1. A tool is preferred over hand-written code only when it reduces total product
   maintenance, not merely local implementation effort.
1. Compatibility residue is a cost center after destructive migration is allowed.

## Authority And Truth

Authority order:

1. Current user instruction.
1. Source code, tests, package metadata, and Git facts.
1. `system/` contracts and schemas.
1. Current docs under `docs/`.
1. OpenSpec specs and active changes.
1. Evidence under `evidence/`.
1. Rules, skills, MCP descriptors, CI files, and host projections.

Generated projections never outrank their source. Host-local memory, agent
session state, generated JSONL, SQLite indexes, caches, and CI-only artifacts
are not repository truth until reviewed and promoted into tracked artifacts.

## Carrier Policy

Use formats by author and lifecycle, not by habit.

| Carrier | Use | Not for |
| --- | --- | --- |
| Markdown | Human judgment, Tao, design, reviews, retrospectives, docs. | Machine-only state or large append-only event streams. |
| TOML | Durable repository config, routing, workflows, manifests, tool catalog, extension manifests. | Public API output or high-volume events. |
| JSON | Command output, MCP payloads, external standards, JSON Schema instances, SPDX, SLSA, in-toto. | Hand-authored repository truth when TOML is clearer. |
| YAML | Ecosystem-native files only: CI, Kubernetes, OpenAPI, action metadata. | ETHOS-owned semantics. |
| JSONL | Generated runtime streams and exports under ignored paths. | Tracked source of truth. |
| SQLite | Ignored local indexes, recall cache, diagnostic state. | Durable repository memory or policy. |
| CUE | Optional schema and config composition adapter. | Core dependency. |
| CEL | Optional guard expression adapter when plain TOML predicates are insufficient. | Universal policy language. |
| OPA/Rego | Optional organization policy gate through subprocess or extension. | In-process core engine. |

## Documentation Progressive Disclosure

ETHOS documentation must reduce agent context load instead of increasing it.
The repository should expose small entrypoints that point to progressively
deeper semantic carriers:

```text
entrypoint -> rule summary -> task-specific rule -> design/reference -> evidence
```

Principles:

1. `AGENTS.md`, `README.md`, and `ETHOS.md` are entrypoints, not semantic dumps.
1. Every entrypoint must point to the canonical carrier instead of restating it.
1. Rules must be concise and operational; long rationale belongs in `docs/`.
1. Skills must be short procedures over repository truth; long reference
   material belongs in docs or direct references loaded only when needed.
1. Generated indexes may help navigation, but they do not become truth.
1. Machine consumers use TOML, schemas, and command JSON; human judgment uses
   Markdown.

Agent loading should be selective:

```text
start -> AGENTS.md -> rules/README.md -> matching rule/skill -> direct refs only
```

Bulk-loading `docs/`, generated artifacts, archived changes, or every skill is
a context failure unless the task explicitly requires broad audit.

## OpenSpec-First Planning Gate

Non-trivial changes to governance semantics must have an OpenSpec carrier before
tracked mutation proceeds. This includes changes to product shape, architecture,
rules, skills, hook policy, scaffolds, projections, release workflow, evidence
policy, or terminal migration planning.

Valid carriers:

| Situation | Required carrier |
| --- | --- |
| New semantic work | New non-complete OpenSpec change. |
| Continued semantic work | Explicit attachment to an active non-complete change. |
| Small typo or formatting repair | No new change if no behavior or governance semantics change. |
| Emergency recovery | Recovery evidence plus later OpenSpec follow-up when semantics change. |

Complete changes are not default containers for new work. They are historical
records unless reopened through an explicit governance decision.

## OpenSpec Product Protocol

OpenSpec is the ETHOS case and specification carrier. It is not a second public
command plane and it is not repository truth by itself. ETHOS uses the official
OpenSpec workspace model, then adds product guardrails around ownership,
lifecycle, evidence, and adopter ergonomics.

The protocol boundary is:

| Carrier | Product meaning | Promotion rule |
| --- | --- | --- |
| `openspec/specs/<capability>/spec.md` | Accepted current capability behavior. | Truth after promotion and proof. |
| `openspec/specs/<capability>/capability.toml` | Capability owner metadata and routing hints. | Routing contract; not behavior by itself. |
| `openspec/specs/families.toml` | Capability family vocabulary. | Taxonomy contract. |
| `openspec/changes/<id>/proposal.md` | Intent, scope, capability routing, reuse stance, and out-of-scope lines. | Planning carrier only. |
| `openspec/changes/<id>/design.md` | Cross-surface design, official/local boundary, trade-offs, rollback, and proof impact. | Required for new, extract, topology, or product-shape work. |
| `openspec/changes/<id>/tasks.md` | Review-sized implementation tasks and lifecycle status. | Execution checklist, not proof. |
| `openspec/changes/<id>/specs/**/spec.md` | Deltas against accepted capability specs. | Merged into live specs only at archive/promotion. |
| `openspec/changes/archive/<date-id>/` | Historical change context. | History after closeout; not a new active carrier. |

Proposal capability bullets must be machine-auditable:

```text
capability=<live-capability>
subject=<stable subject>
reuse=<reuse|extend|extract|new>
change=<add|modify|remove|rename|retire>
facet:lifecycle=<authoring|validation|runtime|archive|release>
facet:surface=<cli|docs|schema|mcp|skill|scaffold|ci|package>
facet:authority=<source|test|schema|docs|openspec|evidence|claim>
```

Only one live capability owns the primary behavior. Secondary impacts are
recorded as impacts, not duplicate normative requirements. Exact live
capability names are the routing contract; aliases and historical labels remain
diagnostics until explicitly migrated.

Capability profiles must evolve from the current minimal metadata into a stable
ontology:

| Field | Duty |
| --- | --- |
| `family` | Human-scale capability family from `families.toml`. |
| `owner.package` / `owner.scope` | Product owner boundary. |
| `primary_invariant` | The one behavior this capability protects. |
| `routing_question` | The question that chooses this capability over peers. |
| `decision_axes` | Facets useful for routing, proof, and review. |
| `recommended_facets` | Valid local hints for proposal metadata. |
| `boundary_rules` | What this capability must not absorb. |
| `proof_profile` | Default and executed proof commands plus required gates. |

`ethos openspec --json` is the product adapter over OpenSpec. Terminal ETHOS
should make it report:

1. Official doctor, status, and strict validation.
1. ETHOS lifecycle review for proposal, design, tasks, deltas, claims, and evidence.
1. Capability profile, family, proposal metadata, and direct-routing health.
1. Live spec topology and live-spec diff guard results.
1. A compact next action that enters through `ethos ...`.

Archive is a product closeout operation. ETHOS should call the official archive
path, then run repo-local guards that the official tool does not own:

1. Active and archived directory state is canonical.
1. Archived `tasks.md` state and progress are complete.
1. Live spec edits are scoped to the archived deltas.
1. Existing scenarios, Markdown links, claim refs, and evidence refs survive.

This absorbs the useful parts of `di-effect`: capability-local profiles,
families, direct routing, reuse stance, dynamic facets, live-spec diff guards,
and archive normalization. It also absorbs `alphasim-dmgr` patterns: a single
command plane, Work Lane aware lifecycle state,
claim/proof binding, topic-scoped closeout evidence, and explicit boundaries
that keep local proof from pretending to be hosted CI or publication.

## Final Design Productization Addendum

The terminal design absorbs external repository lessons as mechanisms, not as
foreign domain vocabulary. From `di-effect`, ETHOS keeps capability-local
profiles, family vocabulary, dynamic routing facets, and direct capability
routing. From `alphasim-dmgr-fix-b3`, ETHOS keeps explicit agent invocation
admission, worktree-first coordination, claim/projection separation, and
topic-scoped closeout evidence. These mechanisms are subordinate to ETHOS
repository truth, Work Lane admission, and the public `ethos ...` command plane.

### Agent Invocation Envelope

Mutation-capable agent work is admitted through an invocation envelope:

```text
intent + owner + target_root + editor_root + write_paths
+ evidence_class + promotion_route + admission_result
```

The envelope is a product contract for host, MCP, and assistant integrations. It
may include optional host-readiness evidence, but host evidence never satisfies
repository proof. Repository mutation remains governed by Work Lane role,
prewrite admission, active claim binding, OpenSpec carrier readiness, and proof
evidence.

### Topic-scoped Evidence

Terminal closeout evidence should be topic-scoped:

```text
evidence/chronicle/<topic>/
evidence/manifests/<topic>.toml
evidence/attestations/<topic>/
```

Each topic records lane, proof class, commands, return codes, retained artifacts,
HEAD binding, digest, and proof boundary. Transitional dated summaries under
`docs/evidence/` remain valid until the terminal `evidence/` root migration
lands, but generated raw streams stay ignored unless summarized into tracked
evidence.

### OpenSpec Product Substrate

A productized OpenSpec workspace includes README guidance, capability family
vocabulary, capability profile templates, active change templates, strict
validation, ETHOS lifecycle review, claim binding, and archive closeout. A bare
`openspec/` directory or syntax-only valid change is incomplete product
governance.

## Product Surfaces

ETHOS must ship more than a CLI:

| Surface | Purpose | Carrier |
| --- | --- | --- |
| CLI | Human and script workflow. | `packages/ethos` |
| MCP | Agent resource, prompt, and guarded tool surface. | `packages/ethos`, `system/surfaces.toml` |
| Skills | Agent workflow packages generated from repository truth. | `.agents/skills/` source, host projections generated as needed |
| SDK | Stable client API for command JSON and governance records. | `sdks/typescript` when needed |
| Distributions | Thin launchers and runner packages. | `distributions/` |
| Scaffolds | Bootstrap and adopt profiles. | `scaffolds/` |
| Extensions | Ecosystem plugins and integrations. | `extensions/` |

The CLI is not the semantic center. All surfaces consume the same contracts,
schemas, and command JSON.

## Terminal Product Repository Layout

This is the desired repository shape after destructive migration:

```text
.
|-- AGENTS.md
|-- CHANGELOG.md
|-- CONTRIBUTING.md
|-- ETHOS.md
|-- LICENSE
|-- README.md
|-- SECURITY.md
|-- .editorconfig
|-- .gitattributes
|-- .gitignore
|-- .gitleaks.toml
|-- .pre-commit-config.yaml
|-- ethos.toml
|-- package.json
|-- pyproject.toml
|-- uv.lock
|-- system/
|   |-- tao.md
|   |-- authority.toml
|   |-- formats.toml
|   |-- routing.toml
|   |-- workflows.toml
|   |-- tools.toml
|   |-- surfaces.toml
|   |-- schemas/
|   |-- policies/
|   `-- projections/
|-- rules/
|   |-- README.md
|   |-- agents.md
|   |-- mutation.md
|   |-- evidence.md
|   `-- release.md
|-- .config/
|   |-- checks/
|   |-- ci/
|   |-- docs/
|   |-- env/
|   |-- ide/
|   |-- mcp/
|   |-- release/
|   `-- security/
|-- docs/
|   |-- index.md
|   |-- start/
|   |-- concepts/
|   |-- architecture/
|   |-- governance/
|   `-- reference/
|-- openspec/
|   |-- config.yaml
|   |-- specs/
|   `-- changes/
|-- evidence/
|   |-- claims/
|   |-- manifests/
|   |-- releases/
|   |-- security/
|   |-- attestations/
|   `-- chronicle/
|-- evolution/
|   |-- ledger.toml
|   |-- memory.toml
|   `-- campaigns/
|-- .agents/skills/
|   |-- README.md
|   |-- activation.toml
|   `-- <skill-id>/
|-- extensions/
|   `-- <extension-id>/
|-- scaffolds/
|   |-- profiles.toml
|   |-- product/
|   |-- minimal/
|   `-- agentic/
|-- packages/
|   |-- ethos-core/
|   `-- ethos/
|-- sdks/
|   `-- typescript/
|-- distributions/
|   |-- npm/
|   |-- homebrew/
|   |-- docker/
|   |-- github-action/
|   `-- gitlab-component/
|-- tests/
|   |-- conformance/
|   |-- integration/
|   |-- unit/
|   `-- fixtures/
`-- examples/
```

### Root Files

| Path | Semantic duty |
| --- | --- |
| `README.md` | Product overview and first-hour usage. |
| `ETHOS.md` | Human governance entrypoint and compressed Tao. |
| `AGENTS.md` | Thin neutral entrypoint that points to canonical surfaces. |
| `CONTRIBUTING.md` | Human contribution workflow. |
| `CHANGELOG.md` | Release history generated or checked by release policy. |
| `SECURITY.md` | Vulnerability reporting and supported versions. |
| `LICENSE` | Legal license. |
| `.editorconfig` | Cross-editor formatting base. |
| `.gitattributes` | Git normalization, export, and language hints. |
| `.gitignore` | Ignored runtime, build, cache, local state, and generated artifacts. |
| `.gitleaks.toml` | Secret detection policy. |
| `.pre-commit-config.yaml` | Local deterministic fallback gates. |
| `ethos.toml` | Repository governance profile and enabled extensions. |

No root file may restate long product design. Root files are entrypoints.

### `system/`

`system/` is the machine governance kernel. It owns contracts, routing,
workflow declaration, surfaces, format policy, schemas, and projection sources.

Required files:

| Path | Duty |
| --- | --- |
| `system/tao.md` | Human source for value judgment and compression. |
| `system/authority.toml` | Authority order and conflict resolution. |
| `system/formats.toml` | Carrier policy. |
| `system/routing.toml` | Subject resolver, stage map, proof-set routing. |
| `system/workflows.toml` | Declarative lifecycle graph and guards. |
| `system/tools.toml` | Tool catalog, profiles, maturity, and gate mapping. |
| `system/surfaces.toml` | CLI, MCP, SDK, skill, CI, and host projection contract. |
| `system/schemas/` | JSON Schema and TOML schema contracts. |
| `system/policies/` | Optional CEL, Rego, or other policy sources. |
| `system/projections/` | Templates for agent and host projections. |

### `rules/`

`rules/` contains concise operational rules. It is not an architecture store.
Every rule must state:

```text
Authority -> Trigger -> Action -> Evidence -> Stop
```

Rules are read by humans and agents. Their authority is lower than code,
tests, schemas, docs, OpenSpec, and evidence.

Terminal rule files:

| Path | Duty |
| --- | --- |
| `rules/README.md` | Rule kernel, placement, and upstream failure-blocking principle. |
| `rules/agents.md` | Agent load order, context refresh, and cross-repository boundaries. |
| `rules/mutation.md` | Work Lane write admission and protected-role mutation rules. |
| `rules/hooks.md` | Context, pre-tool, pre-run, post-write, Git, and CI hook placement. |
| `rules/evidence.md` | Proof, claim, and evidence binding rules. |
| `rules/release.md` | Version bump, changelog, distribution, and publish-readiness rules. |
| `rules/skills.md` | Skill source, activation, and projection boundary rules. |

### `.config/`

`.config/` contains tool-native configuration and execution support. It is
where mature tools read their own config.

`system/tools.toml` decides why a tool runs. `.config/` decides how that tool
runs.

Examples:

```text
.config/checks/ruff/ruff.toml
.config/checks/taplo/taplo.toml
.config/checks/markdown/markdownlint-cli2.yaml
.config/checks/markdown/mdformat.toml
.config/checks/prose/vale.ini
.config/checks/prose/codespell.ini
.config/checks/yaml/yamllint.yaml
.config/checks/yaml/spectral.yaml
.config/checks/sqlfluff/config.ini
.config/checks/shell/shfmt.toml
.config/security/gitleaks.toml
.config/security/osv-scanner.toml
.config/docs/lychee.toml
.config/release/bump-my-version.toml
.config/ci/github/
.config/ci/gitlab/
.config/mcp/
.config/ide/
```

### `docs/`

`docs/` is for human explanation and durable design. It does not hold
machine-only evidence or runtime state.

Terminal docs categories:

```text
docs/start/          first-hour usage
docs/concepts/       core concepts and vocabulary
docs/architecture/   product architecture
docs/governance/     policies and decisions
docs/reference/      stable reference
docs/index.md        navigation
```

The terminal design removes `docs/evidence/` as a proof root. Evidence belongs
under `evidence/`; docs may link to it or summarize it.

### `openspec/`

OpenSpec is the case and change carrier. There is no separate `cases/` root.

```text
Case = openspec/changes/<id> + ethos metadata + evidence refs
```

An OpenSpec change is not truth by itself. It becomes repository truth only
after proof and promotion update source, tests, schemas, docs, accepted specs,
or evidence.

Terminal `openspec/` should be born with enough product guidance that adopters
do not need to reverse-engineer ETHOS itself:

```text
openspec/
|-- README.md
|-- config.yaml
|-- schemas/
|-- specs/
|   |-- README.md
|   |-- families.toml
|   |-- capability.template.toml
|   `-- <capability>/
|       |-- capability.toml
|       `-- spec.md
`-- changes/
    |-- README.md
    |-- template.md
    |-- archive/
    `-- <change-id>/
        |-- proposal.md
        |-- design.md
        |-- tasks.md
        |-- .openspec.yaml
        `-- specs/
```

The scaffolded templates should enforce the product protocol: proposal
metadata, direct capability names, reuse stance, out-of-scope lines, design
evidence for new or extracted capability topology, task status/progress, and
delta sections. The template is guidance; validation must come from schemas and
`ethos openspec --lifecycle --json`.

### `evidence/`

`evidence/` is tracked proof. It owns claim records, release manifests,
security proof, attestations, and judged chronicle entries.

Generated raw streams stay under ignored `.ethos/` and may be summarized into
tracked evidence after review.

### `evolution/`

Evolution is a typed record system, not many independent roots.

```text
evolution/ledger.toml
evolution/memory.toml
evolution/campaigns/<campaign-id>/
```

`ledger.toml` records typed entries:

```text
feedback -> review -> challenge -> hypothesis -> experiment -> evaluation -> retrospective
```

| Type | Meaning |
| --- | --- |
| feedback | Raw signal from users, agents, tools, incidents, or drift. |
| review | Assessment of a change, design, result, or proof. |
| challenge | Adversarial critique that tries to falsify assumptions. |
| hypothesis | Falsifiable improvement claim. |
| experiment | Bounded test of one or more hypotheses. |
| evaluation | Measured result and decision recommendation. |
| retrospective | Human-readable learning after a campaign or repeated pattern. |
| campaign | Long-running goal container that coordinates entries and changes. |

Campaigns are not Work Lanes and they are not a "total lane". A campaign is
the productization orchestration record for a long-running objective. Its
`campaign.toml` manifest is a strict serial graph of OpenSpec-backed Work Lane
steps. Each step records an `ordinal`, `depends_on`, OpenSpec change, Work Lane
branch, claim, evidence refs, and closeout state. The executable closeout unit
remains the Work Lane: each step must prove, land to candidate,
closeout-apply to the accepted root, and retire before downstream steps can
activate or treat it as closed.

`ethos campaign status --json` projects this manifest as `lane_topology`:

| Field | Meaning |
| --- | --- |
| `mode = "strict_serial"` | Only one OpenSpec-backed lane is active at a time. |
| `edges[]` | `depends_on` relationships requiring upstream closeout retirement. |
| `active_step` | The current lane that may mutate and prove. |
| `next_planned_step` | The next lane that can activate after current closeout. |

This absorbs the useful `alphasim-dmgr` campaign pattern: long-running work is
tracked as mission/campaign state with tasks, proof, challenge, and closeout
projection. ETHOS keeps the durable state in tracked campaign manifests,
OpenSpec records, claims, and evidence rather than a hidden local mission
store.

Superpowers can support brainstorming, review, challenge, planning, TDD,
verification, and subagent execution. It is a method pack, not repository
truth. Its outputs become truth only after promotion into `evolution/`,
`openspec/`, `docs/`, or `evidence/`.

### Memory

ETHOS memory must not be a hidden custom database.

| Layer | Carrier | Truth status |
| --- | --- | --- |
| Repository memory | `evolution/ledger.toml`, decisions, OpenSpec, evidence. | Truth after review. |
| Local recall cache | `.ethos/memory/`, SQLite, JSONL exports. | Ignored diagnostic aid. |
| External memory | MCP resources, agent memory, issue trackers, hosted docs. | Context only. |

`evolution/memory.toml` declares providers, promotion rules, retention policy,
and privacy boundaries. It does not store unreviewed memories as truth.

### `.agents/skills/`

`.agents/skills/` is the canonical repository skill source.

`skills`, `.claude/skills`, `.codex/skills`, JetBrains rules, Junie
files, Cursor rules, and other host surfaces are projections or official native
artifacts. They are not canonical ETHOS skill roots.

Projection drift is mandatory:

```text
.agents/skills/ + system/projections/ + system/surfaces.toml -> host projection
```

Generated projection output must carry a source digest and fail drift checks
when stale.

Terminal skill files:

| Path | Duty |
| --- | --- |
| `.agents/skills/README.md` | Skill system overview and portfolio index. |
| `.agents/skills/activation.toml` | Path and intent routing metadata. |
| `.agents/skills/<skill-id>/SKILL.md` | Loadable skill procedure. |
| `.agents/skills/<skill-id>/package.toml` | Skill manifest, capabilities, and quality metadata. |

### `extensions/`

Extensions are how ETHOS grows without making the core large.

```text
extensions/<id>/
|-- extension.toml
|-- README.md
|-- schemas/
|-- gates.toml
|-- policies/
|-- scaffolds/
|-- .agents/skills/
|-- mcp/
|-- adapters/
|-- views/
`-- tests/
```

Plugin execution:

| Trust level | Mechanism |
| --- | --- |
| Trusted in-repo Python | `pluggy` hooks with declared hook specs. |
| Third-party or untrusted | Subprocess JSON protocol. |
| Data-only | TOML manifest, schemas, templates, no Python execution. |

Extensions cannot define Tao, override contracts, bypass workflows, or promote
truth without evidence.

### `scaffolds/`

Scaffolds provide bootstrap and adoption profiles.

| Profile | Purpose |
| --- | --- |
| `minimal` | Add the smallest governance substrate to a repository. |
| `product` | Govern ETHOS itself or a product repository. |
| `agentic` | Add skills, MCP, projections, and evolution support. |

Scaffold execution should use mature template tooling where it reduces code.
The default is declarative manifests plus Copier or Jinja templates behind a
small ETHOS preflight/postflight wrapper. ETHOS owns profile semantics,
rollback, and evidence; the template engine owns rendering.

Bootstrap must install a complete substrate:

```text
README.md
CHANGELOG.md
CONTRIBUTING.md
LICENSE
SECURITY.md
AGENTS.md
ETHOS.md
.gitignore
.gitattributes
.editorconfig
.gitleaks.toml
.pre-commit-config.yaml
ethos.toml
system/
rules/
.config/
docs/
openspec/
evidence/
.ethos/ ignored runtime root
```

The `openspec/` substrate must include config, README files, change and
capability templates, `specs/families.toml`, and a first capability profile
when the selected profile knows the governed domain. An empty directory is not a
complete product scaffold.

### `packages/`

The terminal Python product has two packages:

```text
packages/ethos-core
packages/ethos
```

`ethos-core` owns pure, low-dependency semantics:

```text
ids
result envelopes
schema loading
TOML model parsing
workflow graph validation
guard evaluation
evidence contracts
surface contracts
```

`ethos-core` must not import Git, subprocess, CLI frameworks, MCP SDKs, hosted
forge APIs, SQLite, pytest, or adopter semantics.

`ethos` owns product runtime:

```text
CLI
MCP server
bootstrap/adopt
evidence runner
Git/process adapters
OpenSpec adapter
projection generation
extension loading
release orchestration
diagnostics
```

This collapses the current eight-package ontology because destructive migration
does not need package-level compatibility shells. Internal modules may remain
cohesive, but package boundaries must earn their cost.

### `sdks/`

SDKs are product surfaces, not alternate implementations.

`sdks/typescript` may exist when npm, MCP clients, editor integrations, or web
views need typed access to command JSON and schemas. It must be generated or
schema-bound where practical.

### `distributions/`

Distributions are launchers and runners:

```text
distributions/npm
distributions/homebrew
distributions/docker
distributions/github-action
distributions/gitlab-component
```

They must not duplicate ETHOS product semantics. They call the Python command
plane or package it.

### `.ethos/`

`.ethos/` is ignored runtime state:

```text
.ethos/cache/
.ethos/index/
.ethos/runs/
.ethos/artifacts/
.ethos/exports/
.ethos/memory/
.ethos/views/
```

Nothing under `.ethos/` is truth unless explicitly promoted into tracked
source, docs, OpenSpec, or evidence.

## Governed Repository Layout

`ethos init` or `ethos adopt` must create a complete governance substrate in a
target repository.

Minimal governed repository:

```text
.
|-- AGENTS.md
|-- CHANGELOG.md
|-- CONTRIBUTING.md
|-- ETHOS.md
|-- LICENSE
|-- README.md
|-- SECURITY.md
|-- .editorconfig
|-- .gitattributes
|-- .gitignore
|-- .gitleaks.toml
|-- .pre-commit-config.yaml
|-- ethos.toml
|-- system/
|-- rules/
|-- .config/
|-- docs/
|-- openspec/
|-- evidence/
`-- .ethos/        ignored
```

Agentic governed repository adds:

```text
.agents/skills/
extensions/
scaffolds/
system/projections/
.mcp/ or host-native MCP profile when the host requires it
host projections generated from system/surfaces.toml
```

Generated host surfaces are optional and declared. If committed, they are
checked for drift. If untracked, they are runtime views.

## Workflow Model

ETHOS must not store lifecycle truth in a private state machine database.

State is derived:

```text
OpenSpec change
+ Git facts
+ evidence manifests
+ system/workflows.toml
+ ethos.toml profile
= derived state and allowed transitions
```

`system/workflows.toml` declares lifecycle states, transitions, required facts,
and guard names. The implementation is a generic reducer and guard evaluator
over declared facts.

Use mature libraries where they reduce total code:

```text
tomllib/tomli-w for TOML
jsonschema and referencing for schemas
networkx or a tiny topological validator for graph sanity if needed
pluggy for trusted extension hooks
subprocess JSON for untrusted tools
```

Do not add a heavy runtime state-machine framework unless ETHOS starts running
long-lived processes that need persisted transition execution state. Current
repository governance needs derived state, not an orchestration engine.

## Hook And Guard Mechanism

Hooks are a core governance mechanism. They must be placed where they can
actually prevent invalid state, not only report it after damage.

Hook layers:

| Layer | Timing | Responsibility | Failure action |
| --- | --- | --- | --- |
| Context hook | Before resolving a tool target. | Detect repository root changes, reload `AGENTS.md`, recompute role policy, and refresh status. | Block writes until context is refreshed. |
| Pre-tool hook | Before `apply_patch`, IDE replace, shell write, MCP mutation, or generated file write. | Run equivalent write admission for target paths. | Deny unsafe writes before filesystem mutation. |
| Pre-run hook | Before shell commands with tracked mutation potential. | Classify command risk, repository root, role, and expected output paths. | Require Work Lane or explicit recovery/closeout mode. |
| Post-write hook | Immediately after a write. | Recompute status and compare expected paths. | Fuse the session on protected-root mutation or unexpected paths. |
| Git hook | Pre-commit, pre-push, commit-msg. | Run deterministic fallback gates. | Block commit or push. |
| CI hook | Hosted pipeline. | Prove integration, release, security, and supply-chain gates. | Block merge, publish, or release. |

The mandatory choke point is the pre-tool hook. Git hooks are necessary but too
late to protect against direct tracked file writes.

Normal tracked mutation policy:

```text
target path -> repo root -> context refresh -> status -> prewrite -> write -> post-write audit
```

Protected role policy:

| Mode | Allowed checkout | Allowed mutation |
| --- | --- | --- |
| Normal work | `work/*` Work Lane | Tracked edits after prewrite. |
| Candidate closeout | accepted root command runner plus candidate worktree audit | Only audited fast-forward through `ethos land --closeout`. |
| Violation recovery | protected root with explicit recovery mode | Only rollback, migration to Work Lane, or violation evidence. |
| Publication | accepted root after closeout readiness | Submit branch or release preparation through declared adapters. |

If a host cannot install pre-tool hooks, the agent must call `ethos lane
prewrite` manually before writing. That is a degraded mode, not the desired
terminal product behavior.

## Failure Blocking Must Move Upstream

ETHOS should continually move repeated late failures to earlier stages:

```text
incident -> diagnosis -> rule -> hook -> scaffold/template -> schema/default
```

Stage preference:

| Stage | Example |
| --- | --- |
| Schema/default | Invalid config cannot be represented. |
| Scaffold/template | New repositories are born with the right substrate. |
| Context hook | Wrong repository context cannot be reused. |
| Pre-tool hook | Wrong checkout cannot be edited. |
| Pre-run hook | Dangerous commands require explicit mode. |
| Post-write hook | Unexpected mutation fuses the session immediately. |
| Git hook | Commit-time fallback blocks residue. |
| CI/release | Slow proof blocks integration and publication. |

The goal is not more gates. The goal is shorter distance between intent and
failure. A failure found at publish time should become a CI gate. A repeated CI
failure should become a Git hook. A repeated Git-hook failure should become a
pre-tool hook, scaffold default, or schema constraint.

The accepted-root mutation incident proves a specific missing choke point:

```text
prewrite_guard exists
but write tools can bypass it
therefore prewrite must be bound to mutation capability
```

Terminal ETHOS must treat bypassable guidance as an incomplete control.

## Tool Catalog

`system/tools.toml` declares tool identity, maturity, profiles, gate mapping,
config path, install strategy, and evidence output.

| Concern | Default tool | Config carrier | Profile |
| --- | --- | --- | --- |
| Python format/lint | `ruff` | `.config/checks/ruff/` | minimal |
| Python typing | `ty`; optional `mypy` strict | `.config/checks/ty/`, `.config/checks/mypy/` | product |
| Tests | `pytest` | `pyproject.toml` | minimal |
| Coverage | `coverage.py` | `.config/checks/coverage/` | product |
| Import boundaries | `import-linter` | `.config/boundaries/` | product |
| Dependency hygiene | `deptry` | `.config/checks/deptry/` | product |
| TOML | `taplo` | `.config/checks/taplo/` | minimal |
| Markdown style | `markdownlint-cli2`, `mdformat` | `.config/checks/markdown/` | minimal |
| Links | `lychee` | `.config/docs/lychee.toml` | product |
| Prose | `vale`, `codespell` | `.config/checks/prose/` | product |
| YAML | `yamllint`, `spectral` | `.config/checks/yaml/` | ecosystem |
| JSON/schema | `check-jsonschema`, `jq` | `system/schemas/` | minimal |
| Shell | `shellcheck`, `shfmt` | `.config/checks/shell/` | product |
| Docker | `hadolint` | `.config/checks/docker/` | distribution |
| SQL | `sqlfluff` | `.config/checks/sqlfluff/` | extension |
| Secrets | `gitleaks`; optional `trufflehog` | `.gitleaks.toml` | minimal |
| Python vuln | `pip-audit` | `.config/security/` | security |
| OSV vuln | `osv-scanner` | `.config/security/` | security |
| SBOM | `syft` | `.config/release/` | release |
| Image/package scan | `grype` | `.config/security/` | release |
| Signing | `sigstore`, `cosign` | `.config/release/` | release |
| Attestation | `in-toto`, SLSA provenance | `evidence/attestations/` | release |

Profiles decide which gates run by default. The presence of a tool in the
catalog does not make it mandatory for every repository.

## Docs And Code Consistency

ETHOS must prove docs-code consistency before land and publish.

| Claim | Check |
| --- | --- |
| CLI examples are current | Compare docs examples with command registry and `--help` output. |
| Config keys are current | Validate TOML against schemas and loaders. |
| Package docs are current | Compare architecture docs with package/module layout. |
| OpenSpec specs are current | Compare accepted specs with implemented behavior and tests. |
| CHANGELOG is current | Compare version, release fragments, and release evidence. |
| Links are current | Run `lychee` over docs and root Markdown. |
| Projection surfaces are current | Compare generated digest with source templates and surfaces registry. |
| Evidence is bound | Check HEAD, command, gate profile, timestamp, and digest. |

## Release And Version Bump

Release is a governed workflow, not a command alias.

The release profile must update and prove:

```text
pyproject.toml
package.json
CHANGELOG.md
README examples
docs/reference/command-plane.md
OpenSpec closeout
evidence/releases/<version>.toml
SBOM
attestation
Git tag plan
distribution manifests
```

Use declarative release configuration, preferably `bump-my-version` or an
equivalent lightweight tool for multi-file version replacement. Changelog
generation may use a mature changelog tool only if it keeps `CHANGELOG.md` as
the human release history and does not create a second release truth.

## Low-Code Implementation Rule

Default implementation shape:

```text
declarative TOML registry
+ JSON Schema validation
+ generic reducer/evaluator
+ mature external tool adapters
+ evidence normalization
```

Avoid:

```text
hardcoded gate matrices
parallel command implementations
compatibility wrappers
forwarding modules
catch-all utils
private lifecycle databases
tracked generated JSONL
agent-host-specific truth
```

Python code should mostly:

1. Load TOML.
1. Validate against schemas.
1. Resolve subjects and profiles.
1. Build a declared action graph.
1. Execute tools through a common runner.
1. Normalize outputs into evidence.
1. Render command JSON, human output, MCP resources, and projections.

## Anti-Redundancy Decisions

Terminal design deletes or forbids:

| Surface | Decision |
| --- | --- |
| `claims/` root | Move to `evidence/claims/`. |
| `docs/evidence/` | Move proof truth to `evidence/`; docs link or summarize. |
| `schemas/` root | Move ETHOS schemas to `system/schemas/`. |
| `skills` as source | Replace with `.agents/skills/` source and host projections. |
| `cases/` | Do not create. OpenSpec changes are cases. |
| `contracts/` | Do not create. Contracts live in `system/` and OpenSpec. |
| `govern/` | Do not create. It duplicates `system/`, `rules/`, `evidence/`, `evolution/`. |
| Eight Python packages | Collapse to `ethos-core` and `ethos`. |
| JSONL truth | Keep JSONL generated and ignored. |
| Historical compatibility shims | Delete after destructive migration. |

## Landing Path

Implementation must be staged through Work Lanes, OpenSpec where scope requires
it, and proof. Each stage should be small enough to land independently, but the
design target is not compromised by temporary compatibility.

### Stage 1: Semantic Substrate

Create the terminal substrate:

```text
ETHOS.md
SECURITY.md
.editorconfig
.gitattributes
.gitleaks.toml
ethos.toml
system/
rules/
.config/
evidence/
evolution/
.agents/skills/
scaffolds/
extensions/
```

This stage includes a thin `AGENTS.md`, the initial `rules/` kernel, and the
canonical `.agents/skills/` source. Migrate existing docs and schemas into the terminal
roots. Delete replaced roots after proof.

### Stage 2: Hooked Write Admission

Bind `prewrite_guard` to mutation capability:

```text
context hook
pre-tool hook
pre-run hook
post-write fuse
Git fallback hooks
CI/release proof hooks
```

This stage closes the accepted-root bypass. The product is not safe while
write admission remains voluntary.

### Stage 3: Declarative Core

Implement `ethos-core` around TOML loading, schema validation, routing,
workflow graph validation, guard evaluation, result envelopes, and evidence
contracts.

### Stage 4: Product Runtime Collapse

Collapse current runtime packages into `packages/ethos` modules:

```text
cli/
mcp/
bootstrap/
proof/
git/
openspec/
projections/
extensions/
release/
diagnostics/
```

Remove forwarding modules and package compatibility shells.

### Stage 5: Tool Catalog And Gates

Move gate definitions into `system/tools.toml` and `.config/`. Implement one
runner that executes declared gates and normalizes evidence.

Start with:

```text
ruff
pytest
taplo
markdownlint-cli2
mdformat
lychee
gitleaks
check-jsonschema
```

Then add profile-gated tools for typing, prose, supply chain, release, Docker,
SQL, YAML, and architecture boundaries.

### Stage 6: Bootstrap And Projections

Implement `ethos init` and `ethos adopt` from `scaffolds/profiles.toml`.

Every generated tracked projection must have source digest and drift proof.

### Stage 7: Evolution And Memory

Implement `ethos campaign`, feedback intake, challenge/review records,
hypothesis tracking, experiment evaluation, retrospective closeout, and memory
provider registry.

Use MCP/external memory as recall only. Promotion into repository truth requires
review, challenge, and evidence.

### Stage 8: Release And Distribution

Implement release workflow, version bump, changelog checks, SBOM, security
evidence, attestation, tag planning, npm launcher, Docker runner, GitHub Action,
and GitLab component.

Distributions must remain thin.

## Acceptance Gates

The terminal redesign is acceptable only when:

1. `ethos status`, `plan`, `prove`, `land`, `publish`, and `report` work from
   the terminal layout.
1. `ethos init` can bootstrap a new minimal governed repository completely.
1. `ethos adopt` can add governance to an existing repository without partial
   substrate gaps.
1. MCP manifest and server expose the same command JSON and docs truth as CLI.
1. Skills are sourced from `.agents/skills/` and projections pass drift checks.
1. OpenSpec changes serve as case carriers without a separate `cases/` root.
1. Evidence lives under `evidence/` and runtime artifacts under ignored
   `.ethos/`.
1. The eight-package topology is collapsed to `ethos-core` and `ethos`.
1. Tool catalog gates cover format, lint, links, secrets, schema, tests, docs,
   release, and supply-chain profiles.
1. Docs-code consistency gates pass.
1. Release workflow can bump versions, update changelog, produce release
   evidence, and prepare attestations.
1. Pre-tool hooks make accepted-root tracked mutation impossible in normal mode.
1. Context hooks prevent cross-repository writes with stale injected context.
1. Post-write hooks fuse sessions after unexpected protected-root mutation.
1. Failure patterns demonstrably move upstream over time.
1. No forwarding wrappers, parallel implementations, or compatibility residue
   remain after migration closeout.

## Cold-Start Rule For Future Agents

If chat history is lost, continue from this page:

1. Read `docs/architecture/terminal-governance-product-design.md`.
1. Read `docs/index.md`, `README.md`, and `AGENTS.md`.
1. Inspect current repository shape with `git status --short` and `ethos status --json`.
1. If the checkout is not an owned Work Lane, create or enter one before
   tracked mutation.
1. Run `ethos lane prewrite` for target paths before writing.
1. Create or update one OpenSpec change when the next landing stage changes
   product behavior or contracts.
1. Implement only the next stage with proof.
1. Delete replaced surfaces in the same stage that replaces them.
1. Do not preserve compatibility residue unless the user revokes destructive
   migration authorization.

Status: see front matter.

Purpose: define the terminal ETHOS product design and landing path.

See also: [Documentation Index](../index.md),
[Product Design Contract](../governance/product-design-contract.md), and
[Package Ontology](package-ontology.md).
