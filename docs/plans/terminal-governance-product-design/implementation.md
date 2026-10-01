---
subject: ethos:implementation-convergence
role: explanation
state: active
relations:
  part_of: ../terminal-governance-product-design.md
  constrained_by: ../../governance/product-design-contract.md
---

# Implementation Convergence

Purpose: expand the canonical terminal plan into reviewable implementation choices,
replacement responsibilities and falsifying acceptance. This is one section of
that plan, not a second roadmap or progress ledger.

Read the [canonical order](../terminal-governance-product-design.md#whole-implementation-convergence)
first. [Product meaning](../../governance/product-design-contract.md) remains
authoritative. [Quality](../../../openspec/changes/proof-throughput/tasks.md),
[installed product](../../../openspec/changes/installed-product/tasks.md) and
[formation](../../../openspec/changes/greenfield-formation/tasks.md) own progress.
[Research](../../research/modern-engineering-foundations.md) owns comparative evidence.

For code-level choices, read the [design study](../../research/foundations/code-design.md):
data representation, pure decisions/effects, composition, state alternatives,
batching, incremental work, concrete implementation cuts and rejected drafts.

## Convergence Principles

Navigate by the decision you need; the sections below elaborate the one
canonical plan rather than defining separate workstreams.

| Reader question | Jump to |
| --- | --- |
| How are intent and meaning preserved? | [Intent](#intent-knowledge-and-acceptance), [typed semantics](#typed-semantic-kernel-and-code-observation) |
| How do quality and recovery remain enforceable? | [Quality](#static-repository-quality-and-dynamic-change-admission), [transactions](#transactions-state-and-resource-lifetimes) |
| How do we reduce repeated work without weakening evidence? | [Throughput](#verification-throughput-and-evidence-reuse) |
| What does an installed, extensible product provide? | [Interfaces](#product-interfaces-context-and-ecosystem), [adoption and release](#formation-adoption-distribution-and-release) |
| How do use, learning and knowledge connect? | [Feedback](#reports-observability-and-recursive-feedback), [knowledge](#knowledge-structure-and-visual-projection) |
| Which foundations replace existing implementation? | [Framework decisions](#framework-decisions-and-stop-conditions), [acceptance](#evidence-needed-at-each-cut) |

Optimize complete user outcomes, semantic correctness, recovery, total maintenance
and iteration cost together. Each cut must remove its replaced machinery.
Historical completion and budget snapshots do not override current accepted policy
or fresh evidence.

Token efficiency, iteration speed, UX and DX constrain every cut, not only proof.
Compare cost per accepted outcome: task-relevant context, repeated interpretation
and execution, preparation, review, rework, recovery and consumer decisions.
Progressive disclosure must conserve obligations; optimization must remove work or
concepts rather than transfer them to users. Missing measurements remain unknown.
The [quality Change](../../../openspec/changes/proof-throughput/specs/quality/spec.md#requirement-budget-adjustment-preserves-necessary-behavior)
permits an independent 5,000-ELOC ceiling adjustment only after evidence identifies
necessary complexity and evaluates feasible simplification. Numeric limits remain
in the native source-budget declaration; file and quality limits do not move with them.

Dependencies select execution. Measured critical-path repairs may advance the
canonical plan's assurance cut while meaning and installed-journey work remain active.
Independent read-only comparisons proceed alongside the sole writer.

No new Change or lane is justified merely by another matrix row, framework, report
or incoming message. Complete one admitted cut before expanding its write set.

## What Must Improve

ETHOS must preserve implicit knowledge as explicit, reviewable repository meaning,
make appropriate constraints executable and support learning from actual use.
Its implementation must cover research and alignment through delivery, benefit,
feedback and exit. An elegant transaction kernel alone cannot fulfill this scope.

The recurring implementation failures have related causes:

| Cause | Consequence | Structural correction |
| --- | --- | --- |
| Carrier shape substitutes for meaning | Names, parsed syntax, hashes or checked tasks are treated as stronger evidence than they provide. | Typed identities and relations, explicit interpretation limits, and falsifying observations at the real consumer. |
| The same decision has several owners | CLI, hooks, documentation, CI and adapters drift. | Compile or call the owning decision; remove parallel parsers, constants, policy copies and result interpretation. |
| Internal plumbing leaks to callers | Agents need historical instructions, PATH fixes, internal runtime paths or ordered command folklore. | Complete application operations with discoverable context and typed recovery; test from the installed product. |
| Validation starts too late | A long proof discovers a cheap configuration or binding failure; native providers repeat declared tests. | Resolve dependencies once, run cheap prerequisites first, and reuse precise execution material without reusing authorization. |
| Lifecycle boundaries are implicit | Cleanup loses evidence, an ACK loss causes replay, or a cache becomes an authority. | Give every resource one producer, consumer, lifetime and recovery owner; post-observe before deciding. |
| Feedback becomes prose instead of behavior | The same defect and user correction recur. | Repair the causal owner, add a distinguishing regression, retire the old path, then test the next consumer. |

These are hypotheses to validate at concrete owners, not permission for a blanket
rewrite. Existing code has no preservation privilege; replacement has no privilege
merely because it uses a fashionable tool.

## Architecture And Replacement Cuts

### Intent, Knowledge And Acceptance

Sources: [product meaning](../../governance/product-design-contract.md) and
[intent/adoption comparison](../../research/foundations/adoption.md#intent-formation-and-official-openspec-extension).

OpenSpec owns accepted intent. Separate open interpretation from deterministic
compilation. Interpretations expose source scope, assumptions, negative requirements,
exceptions, tradeoffs and positive/negative examples for acceptance. Every relevant
source constraint is retained, explicitly rejected by an authorized decision, or
unresolved. Coverage of source text does not establish understanding.

Consume official artifact dependencies and resolved output paths, native configuration
and supported schema extension. Remove fixed proposal/design/tasks path inference
and Markdown semantic parsers that duplicate official behavior. Keep `skip_specs`,
removal-only requirements, uncommitted input, archive identity and reopening coherent.
Compile each acceptance claim into its subject, assumptions and falsifying observation;
task completion and broad green tests cannot supply a missing oracle.

Audit historical compression against the recoverable source obligations, including
terminal design, numbered decisions, recursive feedback and adopter instructions.
Recover omitted meaning into its existing owner before retiring raw inputs or archives.
Archive remains history; active code and policy consume current specifications.

Acceptance: reject a mandatory-winner translation of an all-drop request; preserve
renamed artifacts, negative requirements and source links; reach a legal success;
reject stale or insufficient evidence without requiring the user to retell history.

### Typed Semantic Kernel And Code Observation

Sources: [code-design choices](../../research/foundations/code-design.md#data-representation)
and [program-meaning limits](../../research/foundations/semantics.md#program-meaning-is-not-spelling).

Keep Commitment, Facts and TransitionPlan transient; Attestation records required
results without granting permission. Resolve external structure through strict
Pydantic models and use immutable domain values for internal computation. Replace
wide dictionaries, positional multi-value tuples and stringly state transitions
where they hide distinct states. Use discriminated unions, enums where the domain
is closed, `Protocol` at actual substitutable interfaces, `Self`, `override`, and
exhaustive matching with `assert_never`. Preserve Python 3.12 compatibility.

Generate schema and transport descriptions from their one owning model when that
eliminates duplicates. Keep deliberately open payloads only at a documented extension
boundary; an `object` or `Any` crossing into domain decisions needs parsing and narrowing.
Do not replace every small value with Pydantic or add a result-wrapper hierarchy.

Use Python compiler symbol tables for lexical identities, with one bounded
value/effect observation layer. The [executed comparison](../../research/foundations/code-design.md#scoped-inference-comparison)
reserves LibCST for a demonstrated syntax or editing need. Remove spelling-based subprocess/env
recognition, global constant tables and suffix-based inference of executable intent.
Distinguish syntax failure, resolved absence, known consumer, conditional alternatives
and relevant UNKNOWN. Calls through unsupported values do not inherit the names
mentioned inside their expressions. Share exact-source analysis among consumers;
retain proven invalidation before caching. LSP/SCIP and graph tools aid navigation
and impact discovery; they do not become a second authority or deletion proof.

Acceptance: aliases and alpha-renaming preserve observations; shadowing does not
invent effects; later or unrelated assignments do not overwrite call-site meaning;
dynamic uncertainty identifies its affected obligation; public audit, patch admission
and private-boundary consumers agree. Measure cold and repeated analysis cost.

### Static Repository Quality And Dynamic Change Admission

Owners: [quality requirements](../../../openspec/specs/quality/spec.md) and
[gate execution](../../architecture/gate-runner.md).

Resolve applicable obligations once from a universal baseline and explicit language,
repository-kind and risk deltas. Common outcomes include readable structure, source
ownership, reproducible checks, truthful release history and recoverable operation.
Do not impose Python tools or ETHOS's numeric budgets on every language. Generated,
authored, missing and deleted resources have different ownership and next actions.

Cover every Git-tracked carrier with its applicable native checks. Verify selection,
invocation, warning interpretation, result completeness and enforcement separately.
Tighten types across product, tests and tools; enforce module docstrings, private
imports, semantic package placement, formatting, schema, links, secrets, dependencies,
portable execution and source budgets through their existing owners. Enforce positive
contracts for configurable facts instead of growing filename exceptions or blacklists.

Acceptance: unplug or misbind one required capability, weaken one native configuration,
insert a representative semantic error, and show that the public gate rejects it.
Valid authored configuration removal with its consumers remains possible. A clean
inventory and the number of CI jobs cannot prove that these checks are effective.

### Transactions, State And Resource Lifetimes

Sources: [transition planning](../../architecture/transition-plan.md) and
[effect/recovery comparison](../../research/foundations/effects.md).

Use five deep effect implementations: Git refs, worktree/files, Lease/state, remote
publication and runtime/package. Share typed admission/result/recovery semantics;
keep native commit mechanisms and failure boundaries separate. Native Git object
batching, ref transactions, worktrees and compare-and-swap replace duplicate plumbing.

Specify critical state transitions as data and pure guards where it reduces scattered
branches. Use small state models and Hypothesis stateful traces for stale owners,
competing effects, loss of ACK, partial publication and recovery. Use AnyIO task groups,
cancel scopes and explicit deadlines for async work; a process-group/native descendant
owner must still handle termination and supervisor loss. Avoid a second durable engine
for local Git operations. Commands must not each implement their own state machine.

Share immutable content-addressed supply and preparation. Give mutable fixtures and
attempt state exclusive ownership. A cache entry is reusable computation; current
Lease, ref, credentials, authorization and external facts are always reobserved.
Preserve durable evidence before cleanup; distinguish foreign, live, unknown and
proved disposable bytes. Cleanup must be idempotent and bounded after exit and crash.

Acceptance: real process death, stale CAS, lost response and simultaneous writers;
no repeated destructive effect or lost useful result; native macOS/Linux/Windows
cleanup where supported; repeated-run and declared 24/48-hour resource bounds.

### Verification Throughput And Evidence Reuse

Sources: [execution comparisons](../../research/foundations/execution.md) and
[verification limits](../../research/foundations/verification.md).

Optimize time from intended edit to accepted installed behavior, including preparation,
review, execution, integration and cleanup. Separate candidate iteration, verifier
attempt, raw execution material and judgment. Re-render reports or apply a revised
verifier to still-applicable material without rerunning the implementation workload.

Retain native execution results from declared gates so provider verification can
consume the same complete, correctly bound material. Reject missing cases, changed
inputs, stale environment, truncated output and unsupported reuse. Derive reuse keys
from relevant source, data, rules, toolchain, environment and external facts. Test
cache-cleared verdict equivalence; moving HEAD alone is neither sufficient invalidation
nor sufficient reuse authority. Do not stitch focused coverage into a fictitious run.

Use Pants first for the measured dependency-complete test partition; let it replace
corresponding selection, sandboxing, batching and result caching. Keep one evidence
adapter and remove replaced custom execution. Preserve direct native execution where
required by platform/effect semantics. Measure fixture setup, subprocess startup and
runtime materialization before choosing worker counts. Qualify 2/4/8 workers against
the same workload, resource limits and adverse outcomes; no retry-to-green inside proof.

Acceptance: first useful failure occurs before expensive dependents; cold/warm/invalidated
and cache-cleared results agree; native result membership and coverage are complete;
peak resources and total work fall. The current reference bound is 900 seconds with
600 seconds as the next optimization target, subject to the canonical acceptance.

### Product Interfaces, Context And Ecosystem

Sources: [public commands](../../reference/command-plane.md) and
[interface and framework comparisons](../../research/foundations/interfaces.md).

One typed application operation serves CLI, SDK and FastMCP. Each accepts the selected
repository, actor, input and cancellation, and returns a result with evidence and
one executable continuation. Remove CLI-local policy composition, stdout reparsing
and transport-specific decisions. Human output progressively exposes detail; JSON
and protocol stdout remain machine-safe. Short tasks get the smallest justified
proof scope while consequential effects retain their admission requirements.

Ship version-matched Skills, contextual guidance and discoverable command schemas
with the product. Generate slash-command/editor projections from those owners where
a host supports them. Test two Agent implementations without relying on a specific
model or complete chat history. Stable SDK and optional HTTP/A2A adapters consume
the same operations; no always-on service is required for local stdio use.

A capability contract covers identity/version, typed I/O, permissions, cancellation,
idempotency and failure evidence. Python entry points discover installed capabilities.
Use pluggy only for actual multi-provider hook composition where it replaces custom
dispatch. Pre-tool hooks can route, warn or request admission, but native effect owners
enforce repository safety when a host bypasses a hook. Observational plugins cannot
change standards or acquire write authority; plugin failure follows its declared role.

Apply the [hook contract](../../../rules/hooks.md) at mediated write capabilities:
bind current root and exact paths before mutation, then detect unexpected writes.
An unavailable interception boundary is degraded control, not proved protection.
Git/CI fallback and a loaded Skill cannot certify direct-write prevention or isolate
uncooperative same-user writers.

Acceptance: installed discovery, denied/unknown/success results and reconnect agree
across CLI/SDK/MCP; context is sufficient for a new Agent; extension removal works;
an optional observer failure neither authorizes an effect nor destroys its result.

### Formation, Adoption, Distribution And Release

Sources: [adoption profiles](../../architecture/adoption-profiles.md),
[distribution](../../architecture/distribution.md) and
[release governance](../../governance/release-governance.md).

Greenfield produces a usable foundation: purpose, native repository conventions,
quality baseline, real identity, first accepted Change, guidance and recovery.
Domain generators remain replaceable. Brownfield discovers and preserves layout,
customization and earlier history; adoption does not retroactively certify it.
Retain generator/version/input provenance for old/current/new upgrades, use Copier
where it replaces custom three-way template evolution, and surface real conflicts.

Prefer a shared immutable product distribution with a small repository selector and
local state. Compare portable interpreter plus wheel, native Homebrew packaging and
PyInstaller against the same installed lifecycle before selecting the builder. npm
may supply official OpenSpec internally; it is not by itself an ETHOS distribution
strategy. A consumer must not require an ETHOS source checkout or ambient project Python.

Build new generations, validate state compatibility, switch selection/hooks/state,
post-observe and retain rollback until consumer-safe retirement. Publish macOS/Linux
through Homebrew and native release assets; qualify Windows explicitly. SemVer,
Keep a Changelog, source/tree/package identity, tags, signing/notarization and registry
publication each have an owner. Shared signing credentials belong to their team and
credential store, while per-project requests bind product-specific effects.

Acceptance: clean install, retained-state upgrade, interruption, rollback, offline
operation and live-consumer-safe uninstall; two repositories share immutable supply
without sharing state; each declared Forge exposes the same selected objects/assets;
partial publication reports actual effects and resumes without rebuilding or resigning.

### Reports, Observability And Recursive Feedback

Sources: [verification and reporting](../../research/foundations/verification.md)
and [recursive domain feedback](../../governance/product-design-contract.md#recursive-domain-feedback).

Use JUnit, coverage and SARIF where native consumers support them. Allure 3 derives
human/Agent reports, steps, attachments, environment, history and attempts from the
same execution; failures in setup, teardown, cancellation and non-test gates remain
visible. Verify uploaded reports through both Forge consumers, including source identity.

Use OpenTelemetry for optional tracing of application calls, attempts, child processes,
queue/setup/body/cleanup and native effects. Bind existing operation identities;
redact secrets, bound cardinality and retention, and keep required evidence unsampled.
This replaces bespoke trace plumbing; it is not another evidence authority.

Feedback operates on actual use, methods/implementation, governing models/purpose,
and the feedback mechanism itself. Bind benefit observations to deployment identity,
baseline, environment and window; a counterexample revises applicability and may
propose new intent without rewriting history. A model gap requires promotion of the
smallest necessary distinction, dependent migration and retirement of the old model.
Inspect AI/DSPy can evaluate replaceable capabilities on held-out tasks; scores never
compensate for hard-constraint violations or grant repository permission.

Acceptance: observe a real outcome in self-hosting and a distinct business adopter;
trace a failure to the original assumption/requirement/implementation; repair the
owning mechanism and demonstrate changed behavior in the next attempt. Note-only,
stale and contradictory closure is rejected. Keep progress in existing tasks.

### Knowledge, Structure And Visual Projection

Owner: [documentation reading contract](../../governance/docs-registry.md#human-and-agent-reading-contract).
Comparison: [documentation and interchange](../../research/foundations/documentation.md).

Organize by semantic responsibility and reader question. README is a boundary's
entrance and navigation; stable numbered decision records preserve necessary reasons.
Split long current documentation by coherent topics and links, retaining each unique
obligation. Apply the accepted 500-nonblank-line scope; release history, official
OpenSpec artifacts and declared generated output keep their own lifecycle rules.
Audit specs/Skills taxonomy for duplicate authority, missing coverage and catch-all
topics. Prefer native configuration under `.config` and TOML where supported.

Use Diataxis as a reader-oriented organizing principle, not mandatory template count.
An OKF adapter is justified by a real interchange consumer and must preserve identity,
unknown fields and declared loss. Architecture, brand assets, rules and Skills remain
projections; refresh semantic sources before hashes. Preserve original visual design
strengths and prove visible meaning/readability independently from geometry or IDs.

Acceptance: both a human and a fresh Agent find the relevant owner with bounded context;
links and source relations survive moves; compressed historical meaning is accounted
for; removing an obsolete carrier leaves no active consumer or unique lost obligation.

## Framework Decisions And Stop Conditions

Admit a foundation only if hard behavior and trust constraints hold and the measured
total benefit includes migration, adapter code, operations, supply, storage, recovery
and maintenance. Establish an incumbent baseline and one representative adverse case
before each trial. After one bounded workload and at most one justified repair, decide
adopt or reject for that responsibility; record a specific new trigger for reopening.
No indefinite “later” state and no requirement to adopt every listed tool.

### Meaning And Code

| Foundation | Decision for the planned cut | Acceptance and replaced implementation |
| --- | --- | --- |
| Strict Pydantic, immutable dataclasses, Python typing | Adopt at actual boundary/domain needs; deepen existing use. | Remove repeated shape checks, broad internal payloads and positional tuples; preserve schema and minimum Python behavior. |
| CUE + CEL | Continue implemented ownership: CUE composes/projections; CEL evaluates typed predicates. | One source change reaches both Forges; no duplicate policy interpreter; invalid/non-Boolean predicates reject. |
| Compiler symbol tables / LibCST | Use compiler-native scopes for the current observation repair; reserve LibCST for a demonstrated syntax/editing need. | Qualify value/control-flow limits, public UNKNOWN behavior and analysis cost; remove spelling heuristics without treating metadata as full inference. |
| CodeQL/Semgrep, LSP/SCIP, graph algorithms | Use targeted analysis/navigation where its evidence exceeds cost. | Explicit language and flow coverage; a missing edge cannot justify deletion or a new permanent ontology. |
| Rust / Go / TypeScript | Permit bounded implementations when they remove more build/interface/operational burden than they add. | Same public contract, cross-platform evidence and total cost accounting; no wholesale rewrite justified by line displacement. |

### Execution And Supply

| Foundation | Decision for the planned cut | Acceptance and replaced implementation |
| --- | --- | --- |
| mise + uv + Nox | Keep distinct native-tool, Python-lock and public session responsibilities. | One prepared child environment, exact native diagnostics and no duplicate installation/selection; retire wrappers with no semantic work. |
| Pants | Select the measured dependency-complete test partition for production qualification. | Full input closure, cold/warm/cleared-cache parity, native reports and less work; retire equivalent scheduling/materialization. |
| Dagger / BuildKit | Execute one real source-to-wheel/OCI comparison before settling the container builder. | Include setup, source invalidation, failure and cleared cache; adopt only when it removes duplicate local/provider assembly. |
| Nix / uv2nix | Execute one Unix package-closure comparison if the package cut still needs custom native assembly. | Derive from uv.lock, independently rebuild, run outside Nix and measure total cost; otherwise reject that scope as already satisfied. |
| Bazel / Buck2 / Pixi | Do not add as parallel ETHOS execution owners. | Reopen only for a measured Pants/native capability gap or adopter-native environment requirement. |

### Effects And Evidence

| Foundation | Decision for the planned cut | Acceptance and replaced implementation |
| --- | --- | --- |
| AnyIO + native process primitives | Deepen existing lifetime/cancellation implementation. | Real descendant/supervisor failure, deadline and cleanup; remove duplicated command-specific supervision. |
| State models + Hypothesis; TLA+/Quint selectively | Adopt small executable transition models and stateful tests. | Reproduce stale/CAS/recovery/all-drop traces; no second persisted lifecycle. |
| Temporal / Restate / DBOS | Reject as the local repository transaction foundation. | Reconsider only for a demonstrated remote durable-operation need exceeding current effect receipts and native recovery. |
| Allure 3 + OpenTelemetry | Complete reporting; add bounded optional standard tracing. | Same-run complete results, diagnostic retrieval without reruns, redaction and controlled cost; retire custom report/trace duplication. |
| in-toto/DSSE/SLSA/TUF and SBOM formats | Use bounded interchange/update adapters for real release consumers. | Preserve original identity, prior trust, material/product boundaries and loss; signatures do not certify semantic correctness. |

### Product And Extensions

| Foundation | Decision for the planned cut | Acceptance and replaced implementation |
| --- | --- | --- |
| FastMCP + typed application operations | Continue selected stdio framework and unify all public transports. | Real installed client, cancellation, root/actor binding and error/UNKNOWN conformance; remove transport policy copies. |
| Entry points / pluggy / WASI | Use entry points for discovery; pluggy only for actual hook multiplicity; no WASI runtime absent a proved isolation need. | One capability contract, denial/cancellation/removal, and deletion of replaced dispatch; discovery never grants authority. |
| Copier + native domain generators | Use where they replace template generation/evolution machinery. | Preserve customization, exact provenance, conflict and rollback; no imposed domain layout or generator authorization. |

## Evidence Needed At Each Cut

Record one causal counterexample, the existing owner, migrated unique obligations,
removed implementation, affected consumers and observed result in the current Change
and receipts. Freeze complete source inputs before full proof; integrate and activate
through native admission, then reobserve installed and remote effects before retirement.
Source acceptance may precede complete delivery; keep remaining obligations open.

Measure false admission/blocking, preserved useful outcomes, repeated effects,
first-actionable-failure and accepted-runtime latency, cold/warm work, process/RSS,
bytes/inodes, recovery/handoff effort, maintenance touchpoints and task-relevant context.
Do not substitute test count, raw ELOC, framework count, cache hits or one fast sample
for those outcomes. Numeric constraints stay at their current executable owners.
