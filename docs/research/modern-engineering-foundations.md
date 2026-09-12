---
subject: ethos:modern-engineering-foundations
role: research
state: active
relations:
  informs: ../plans/terminal-governance-product-design.md
  constrained_by: ../governance/product-design-contract.md
---

# Modern Engineering Foundations

Status: active research; recommendations are not accepted implementation.

Purpose: compare foundations against the full product mission, identify
replacement/deletion opportunities, and state evidence and unresolved limits.

See also: [Product Design Contract](../governance/product-design-contract.md) and
[Terminal Governance Product Design](../plans/terminal-governance-product-design.md).

## Question And Conclusion

Which mature foundations can replace ETHOS machinery while improving preserved
meaning, safe progress, feedback time, adoption and maintainability?

The scope is the complete [Product Design Contract](../governance/product-design-contract.md):
problem and value, research, interpretation and tradeoffs, accepted intent,
compilation, capability composition, collaborative execution, verification,
delivery, observed benefit, learning and exit. A compiler, graph or transaction
engine covers only part of that responsibility. This report informs the
[existing terminal plan](../plans/terminal-governance-product-design.md); it is
neither a second contract nor an implementation queue.

The recommended direction is a small domain-owned trust kernel over native
repository effects, declarative constraints, replaceable execution and standard
interchange. ETHOS should own the meaning and admission of a change, not invent
another tool installer, parser, process supervisor, test dashboard or distributed
workflow platform when a suitable foundation can replace it. Conversely, a tool's
cache, task state, signature, graph or report must not acquire acceptance authority.

There is sufficient evidence to prioritize replacements, but not to select a
universal execution engine or claim a measured whole-product improvement. In
particular, earlier dismissal of Pants or a substantial redesign was unsupported
by a common ETHOS workload comparison. That conclusion is withdrawn. The present
runner is a baseline to beat, not a reason to preserve itself.

## Evidence And Limits

Research date: September 12, 2026, Asia/Shanghai. Collection used authenticated
GitHub read-only APIs, official documentation and bounded local commands. Source
links below pin commits; a default-branch snapshot is not evidence that its
features shipped in a stable release. No evaluated tool was installed, upgraded
or configured in ETHOS by this research.

| Claim | Evidence | Boundary |
| --- | --- | --- |
| Authoring baseline | HEAD `4dd2f442eb6cae9477d8599ca990d708820d0a8c`, committed tree `d03c47380c7e9612e1e6b8df7069a754c5588b6e` | Working tree also contains uncommitted runtime-reader-handoff work; HEAD does not describe those edits. |
| Accepted baseline | HEAD `d9a936edb49247d31e6dd4356ad00fd7d8c889cf`, tree `c1d155b35f0efe43a624d5d6684a0ddedf69fb5f` | Acceptance and runtime selection have not advanced in this research. An unrelated untracked browser output was observed and left untouched. |
| Available tools | mise 2026.9.5, Pixi 0.80.0, Dagger 0.21.9 and Git 2.55.0 version commands succeeded | Availability does not prove an ETHOS integration or any performance benefit. |
| Native hook transport | Isolated Git repository, command-scoped configured reference hook: valid update succeeded; rejection in prepared phase aborted update; exact old ref remained; config bytes unchanged | A 0.331-second local probe, not a benchmark, security proof or resolution of incumbent-reader migration. Scratch root was removed. |
| Current gate scheduling | Gate runner already uses dependency-ready scheduling; Python tests use work stealing | Replacing obsolete barrier waves is not a current improvement. The external command path has no explicit subprocess timeout; that alone does not prove the historical hang cause. |
| Budget policy change | Native budget report passed with product 41,407 and tests 43,172 against independent 50,000 limits; 74 existing budget regressions passed in 3.15 seconds | Working-tree measurement and focused tests, not exact-source full proof or installed delivery. Numeric owner changed; measurement and exclusions did not. |
| Comparative engines | Source and protocol inspection for Pants, Dagger and alternatives | No common cold/warm/cache-cleared ETHOS workload was executed. No relative speed or code-deletion estimate is established. |

The existing ignored evidence home contains the collection receipts:
`build/evidence/quality/evidence-retirement/foundations-*.json` and
`foundations-budget-regressions.log`. They retain source commits, document
SHA-256 values, selected passages, failed retrievals and actual probe output.
They are diagnostic evidence, not tracked authority. Durable conclusions and
reproduction conditions are here; raw upstream repositories are not vendored.

### Whole-Product Coverage

| Responsibility | Foundations considered | Recommended disposition and ETHOS responsibility |
| --- | --- | --- |
| Research and intent alignment | Official OpenSpec customization, Inspect AI, DSPy | Use native context/rules and falsifying examples. Capability evaluation may improve interpretation; only accepted intent enters deterministic compilation. |
| Specifications and executable constraints | CUE, JSON Schema, CEL, Cedar; bounded SMT verification | Trial declaration consolidation and typed guards. Keep one owner for each rule, including trusted prior policy. |
| Code and repository meaning | Compiler metadata, LibCST, LSP, Tree-sitter, SCIP, CodeQL, graph algorithms | Separate syntax, binding, flow and effect observations. Unknown semantic coverage must remain visible. |
| Cooperation, competition and exploration | Native Git object/ref/worktree mechanisms, small state models, Hypothesis | Preserve multiple contributions, zero/one competitive winners, all-drop and useful negative results; an engine cannot redefine these outcomes. |
| Process and failure management | Standard-library structured concurrency, AnyIO, statecharts, Temporal | Replace repeated cancellation/process supervision where justified. Keep current authorization and resource-specific effects outside replay. |
| Build, test and reuse | Pants, Dagger, Bazel, uv, mise, Pixi, Nix | Compare coherent alternatives; do not stack multiple schedulers or resolvers over the same inputs. |
| Verification and reports | Hypothesis, mutation testing, Allure 3, native JUnit/coverage | Reuse execution results for human and agent views without replacing proof judgment or hiding incomplete execution. |
| Extensibility and interoperability | Python entry points, pluggy, MCP, A2A, WASI | Small versioned capability interfaces; optional protocol adapters; permissions and failure behavior remain explicit. |
| Delivery and updates | Native Git, in-toto/DSSE, SLSA, TUF, CycloneDX | Bind exact subjects and provenance, distinguish update trust from activation and Forge observations. |
| Formation, adoption and upgrades | Copier, official tool templates, native environment managers | Generate candidates; preserve customization and upgrading basis; validate conflicts and complete uninstall/re-entry. |
| Observability and feedback | OpenTelemetry, CloudEvents, Inspect AI/DSPy | Observe attempts, effects and outcomes separately; external observation proposes new intent, not new authority. |
| Documentation and knowledge | Diataxis, OKF, native API/schema generation | Organize by reader need and semantic owner; references/projections must not become an independent intent or attestation store. |
| Product interfaces and languages | Existing Python CLI, typed SDKs, Rich; Rust, Go, TypeScript | Choose implementation language by bounded responsibility and measured total cost, not Python ELOC displacement. |

## Intent Formation And Official OpenSpec Extension

[Official OpenSpec customization][openspec-customization] supports project
context and per-artifact rules, with custom schemas when actual artifact
dependencies need to differ. Prefer the smallest native extension that expresses
an accepted need. Use custom schemas only after testing official generation,
status, validation, synchronization and archive; do not fork the parser or copy
its task state machine into ETHOS.

For the full intent path, keep source observations and unresolved interpretations
explicit, read back positive and negative cases, then accept one meaning before
deterministic compilation. An all-drop exploration cannot be translated into a
mandatory winner. Schema validity and provenance coverage do not prove that the
interpretation is correct or the checks are sufficient to falsify it.

Implementation acceptance and post-archive publication outcomes are different
obligations. Do not require an immutable archive to hold future mutable task
progress, nor check off publish/retire before their effects. Use an already owned
release operation or subsequent official Change where appropriate, retaining
source/result links and the full delivery goal. The recent AIGW task-cycle report
requires a public-path regression; this research has not established a currently
working accepted-runtime solution or created another release carrier.

## Toolchain And Environment Ownership

The release API reported mise `v2026.9.5`, Pixi `v0.80.0`, CUE `v0.17.1`, Pants
`release_2.33.1`, Dagger `v0.21.9` and Allure `v3.17.0` as their latest
non-prerelease tags at collection. These are observations, not permanent pins or
an authorization to auto-upgrade. A selected dependency needs supported-platform,
license, integrity, locked-supply and failure-path verification.

| Candidate | Verified capability | Replacement test |
| --- | --- | --- |
| [mise][mise] | Release documentation separates requested versions from resolved tool artifacts and supported checksums; [security controls][mise-security] distinguish config trust from artifact verification | Strong candidate for developer/CI tool bootstrap. Replace duplicated binary discovery/download/version checks only where its backend guarantees suffice. Keep ecosystem locks for package dependencies; mise's lock does not lock every external dependency. |
| [Pixi][pixi] | Cross-platform, multi-language environment management; [environment contract][pixi-environment] binds synchronization to its lock | Compare an integrated native tool environment against the present Python/Node supply. Require offline installation, exact platform closure and coexistence with a separately distributed ETHOS package. A Pixi environment is not ETHOS runtime activation. |
| [uv][uv] | Python project, interpreter and package management with a shared cache | Treat as a strong baseline for Python, not a mandated permanent choice. Remove local dependency-resolution substitutes while retaining ETHOS acceptance, immutable inventory and selector responsibilities. |
| [Nix][nix] | Declarative build/package foundation | Reference candidate for reproducible supply and content-addressed builds. Native Windows delivery and user adoption cost need independent evidence; no blanket cross-platform claim. |

mise's [artifact cache][mise-cache] is explicitly experimental in the inspected
release; ordinary freshness checks use modification times. Neither is an
acceptable substitute for complete proof-input identity. Do not put proof trust
on an experimental convenience cache merely because the tool itself is stable.

Choose either a split ownership model, such as tool bootstrap plus native Python
and Node locks, or an integrated environment model. Independent package manifests
remain necessary for distributed packages; duplicated editable resolutions for
the same runtime do not. The experiment must name precisely which installers,
launchers, discovery rules and supply copies disappear.

## Execution, Reuse And Failure Latency

[Pants][pants] is the leading native dependency-aware execution candidate to
compare with the current scheduler. Its [process implementation][pants-process]
has explicit cache scopes, including per-session deduplication without durable
reuse. Dependency inference, declared environment inputs and process isolation
can remove home-grown selection/materialization/cache logic. They do not infer
all mutable Git metadata, lock owners, credentials, remote facts or undeclared
host observations. Native Windows coverage remains unestablished by this review.

[Dagger][dagger] is the leading containerized build/package execution candidate.
The inspected release offers typed container/file/Git operations, reusable
execution and OpenTelemetry output. It can replace repeated CI shell and container
setup while keeping local and CI invocations aligned. A container running on a
Mac does not test native macOS process/file semantics; Linux containers do not
replace native Windows verification. A mutable cache volume is not an immutable
proof input, and a Git mirror is not itself the selected source snapshot.

[Bazel][bazel] and Nix are comparison references when their execution or supply
model fits better. They are not rejected because the repository has one package,
nor admitted because they are large foundations. Selection requires the common
workload below. Native tests and governed mutable effects may legitimately remain
outside a selected build engine, under one explicit resource contract.

Current replacement targets are the scheduling/process portion of
`src/ethos/adapters/gates/runner.py`, repeated setup in
`tools/ci/python_test_gate.py`, and materialization under
`src/ethos/adapters/repo/runtime/materialization/`. Do not delete the gate
obligation registry, proof binding, native effect tests or immutable runtime
selection merely because an engine can execute commands.

Optimize the whole feedback interval: cheap deterministic failures first;
reuse an unchanged, still-applicable execution result; do not replay a heavy
suite to change presentation; freeze before full proof; observe real effect
results before retry. A dependency-aware queue already exists, so the next
comparison concerns input completeness, setup duplication, isolation and process
lifetime, not a superficial scheduling rewrite.

## State, Hooks And Effects

[Git's native configured hooks][git-hook] and [configuration contract][git-hook-config]
provide composition without another script dispatcher. The local isolated probe
used command-scoped configuration only; no ETHOS hooks were disabled or modified.
It observed preparing, prepared and committed phases on success, and prepared
rejection followed by aborted. Supported phase handling, hook order, trust and
config precedence require explicit tests before adopting this transport.

This does not solve the current handoff by itself. Adding a successful hook
cannot neutralize an incumbent hook's rejection, and using a generic disable
switch would discard the very boundary being preserved. The remaining design
must let an explicitly authorized exact evaluator run the same substantive
admission once, with normal raw-Git behavior unchanged. If a native mechanism
cannot preserve that obligation, its convenience is not an adoption argument.

[Native ref transactions][git-ref] supply precise old-OID checks and ref effects.
They do not make filesystem, database and multi-Forge effects one global atomic
transaction. Native command observation is not universal interception; there is
no assumed pre-status hook. Pre-tool events, where a host supports them, should
call the existing owner for early failure and context selection. They are not
an agent-independent security boundary for writes made outside that host.

| Layer | Suitable foundation | Required distinction |
| --- | --- | --- |
| Pure legal transitions | Small typed transition model; [pytransitions][pytransitions] or [SCXML][scxml] where hierarchy/events reduce code | A legal transition does not establish fresh facts, permission or effect completion. Do not persist another copy of repository state. |
| UI interaction | XState | [Restoration][xstate] does not rerun completed actions but restarts invocations. It therefore does not guarantee exactly-once external effects. |
| Local process lifetime | Standard-library task groups/timeouts; [AnyIO][anyio-mechanism] if it replaces repeated supervision | Cancellation of a coroutine is not proof that its external process tree stopped. Threads may require cooperation; cover real process death and cleanup. |
| Long-lived external operations | [Temporal][temporal] as an optional execution backend | Durable orchestration can own its attempts/history, not repository intent, Lease or authorization. Require idempotent/observed effects and fresh admission on each effect. |

Prefer a small explicit model and native effects for local repository governance.
A durable engine becomes justified by measured long-lived external coordination,
not as a cure for an ambiguous model. Attempt, effect, durable result and ACK must
remain distinguishable whether implemented directly or through a framework.

## Declarative Constraints And Semantic Analysis

[CUE][cue] is a serious candidate to consolidate configuration composition and
validation. [CEL][cel] is a serious candidate for bounded pure policy predicates;
it is already a declared ETHOS dependency, not an entirely absent capability.
[JSON Schema][jsonschema] remains an interoperability option for wire structures.
These serve different layers, but overlapping manually maintained definitions do
not become legitimate merely because each is in a different language.

Trial one real duplicated rule family: choose one editable declaration owner,
derive all necessary projections, reject contradictions before execution, and
compare canonical meaning and error paths. Remove superseded validators and
schemas in the same migration. CUE unification does not understand user intent;
CEL parsing does not imply static type checking, boolean result correctness or
bounded evaluation in the selected implementation. A dynamically typed context
can defer misspellings until runtime. Candidate policy cannot weaken its trusted
predecessor to approve itself.

[Cedar][cedar] is worth comparison if entity/relationship authorization becomes
the specific duplication to remove. It is not a second general policy language
to add alongside CEL without an ownership partition. [CEL's Java verifier][cel-verifier]
and [Quint][quint] offer useful bounded reasoning experiments. The inspected CEL
verifier leaves some functions uninterpreted and bounds dynamic comprehensions;
UNKNOWN outside its supported proof boundary is not a universal theorem.

Use the smallest formal model that can expose stale generation, duplicate effect,
missing success path, bad policy replacement or lifecycle cycles. Translate a
counterexample into a real public-entry regression. A proof about a model is not
an implementation proof without a checked correspondence and explicit assumptions.

### Program Meaning Is Not Spelling

The current `python_syntax.py` still constructs a whole-tree string table and
recognizes certain calls by owner spelling. Earlier independent public-gate
probes demonstrated alias, shadowing and program-point counterexamples. This
review re-observed the mechanism, but did not replay that public workload at the
current dirty source; it does not assert full proof or publication bypass.

[LibCST's scope implementation][libcst-mechanism] handles names, assignments and
access relationships. It is a candidate to replace spelling-based binding
heuristics, not a complete value-flow/effect interpreter. [Tree-sitter][tree-sitter]
is useful for incremental syntax, [LSP][lsp] for language-service capabilities,
and [SCIP][scip] for semantic indexing. The inspected LSP 3.17 document calls
itself a previous revision; it is not a current-version recommendation. Each
observation must carry its source,
provider, supported semantics and completeness boundary. No syntax tree or symbol
index automatically proves behavioral equivalence.

[CodeQL][codeql] is a stronger flow-analysis candidate for selected high-risk
questions, subject to execution, language support, licensing and maintenance
cost. [NetworkX][networkx] is a reusable graph algorithm library, not a reason to
persist a second semantic graph. Derive dependency, impact, reachability and
orphan views from owners. Structural isomorphism is a useful duplicate candidate
signal only when node/edge meaning, effects, assumptions and boundaries agree.

Move supported cases into the unique observation owner, delete substituted
heuristics, and test aliasing, alpha-renaming, local shadowing, reassignment,
conditional import, unresolved dynamic call and legitimate negative cases.
Unsupported dynamic behavior produces relevant UNKNOWN, not a global permanent
block. Code semantics must not narrow the full product chain.

## Extension Contracts, Isolation And Interoperability

Use standard Python entry points for installed capability discovery; use
[pluggy's registration and hook validation][pluggy-mechanism] only where genuine
multi-provider hook composition would otherwise be reimplemented. Discovery,
selection, trust and arming are separate observations. In-process plugins share
the process's privileges; a plugin API is not a sandbox.

[MCP][mcp] and [A2A][a2a] are protocol candidates for tools/resources and agent
collaboration. Expose existing typed capabilities through thin adapters; remote
task identifiers and protocol state cannot replace official Change or Lease
state. An adapter must declare identity/version, permission scope, cancellation,
timeouts, retry behavior, result provenance and unsupported semantics. All agents
and models consume the same authority; none is hard-coded as the product owner.

[Wasmtime/WASI][wasmtime] is worth a bounded trial for genuinely untrusted,
portable capability code with restricted imports, filesystem and resource use.
Admission requires actual sandbox escape/resource tests and usable bindings, not
an assumption that WebAssembly alone provides the needed isolation. Native
capabilities and separate processes remain possible alternatives. No marketplace
or universal plugin runtime is needed before independent implementations pass
one shared conformance workload.

## Verification, Reporting And Observability

[Hypothesis][hypothesis], targeted mutation testing and real effect traces should
replace repetitive example scaffolding where they preserve or strengthen failure
sensitivity. Keep semantic scope separate from resource cost. A pure rule test
should not install a full runtime; a ref/process/lock boundary needs the real
resource. Shared fixture code and copied assertions are not independent evidence.

[Allure 3][allure3] deserves a report-only prototype against existing results,
not rejection as decoration. Its inspected release has a TypeScript implementation,
modular report plugins and human/agent-oriented views. Evaluate useful dimensions:
requirements/scenarios, steps, attachments, environments, attempts, failure
classification, history and partial execution. Allure TestOps would introduce a
separate service and management concern; it is not required to produce reports.

Keep JUnit and coverage interchange for native Forge consumers. Generate Allure
from the same actual execution results, not a second test run or a manually
maintained test inventory. Include every declared verification plane, including
setup errors, skips and incomplete/cancelled gates. Missing results must not
appear green. Open reports on both configured Forges and verify their exact source
identity; an uploaded artifact or screenshot alone is insufficient acceptance.

[OpenTelemetry][opentelemetry-mechanism] is the preferred observation substrate
to trial instead of custom tracing. Correlate intent/source/runtime, candidate
iteration, verifier attempt, command, owned resource, external effect and receipt.
Keep high-cardinality identities in suitable traces/logs rather than uncontrolled
metric labels. Export is optional and failure-bounded; secret redaction and
retention are mandatory. Telemetry loss cannot grant authority or erase the
existing effect result. [CloudEvents][cloudevents] is a candidate envelope only
when event interchange has a real consumer; it does not guarantee delivery,
ordering or exactly-once execution.

Observe queue/setup/body/teardown time, process count, bytes/inodes and cache work,
then optimize the measured bottleneck. Report first actionable failure latency,
whole-change completion time, false blocks, false passes, repeated effects,
retained useful outcomes and agent handoff cost. Test counts and ELOC alone do not
prove quality or effectiveness.

The native staged-secret check exposed a false positive before source freeze:
Gitleaks 8.30.1's Sourcegraph rule accepted any 40-hex string when a provider name
occurred in the fragment, so four authentic Git OIDs in this report were flagged.
The [upstream change](https://github.com/gitleaks/gitleaks/pull/2083) proposes the
same prefix correction but was still open at inspection. The existing native
rule now requires the provider token prefix; inherited generic credential rules
still reject unprefixed token assignments. Five executed native cases distinguish
three token forms, a legacy assignment and a non-secret Git OID. The staged source
passes without removing source hashes, suppressing findings or excluding files.

### Tool Depth Is An Executed Feedback Loop

A September 13 local-time diagnostic scanned 489 Python files from the then-dirty
`4dd2f442` worktree in 0.071 seconds with native scc 4.1.0 cognitive, unique-line
and character analysis. This is a bounded runtime observation, not a benchmark or
the official ELOC measure. Per-file cognitive leaders included Python reference
observation, OpenSpec scope, prewrite, hook activation and proof CLI. Ranking alone
does not establish a defect, duplicate behavior or safe deletion.

Native history reports were tried separately with depth 100. Both fail because
scc's pinned go-git reader rejects the repository's `worktreeConfig` extension.
Do not downgrade Git configuration for a diagnostic. The release's single reader
owner is [git_open.go](https://github.com/boyter/scc/blob/c651b07a7d3aa6e97a476380eef0f478a53719a3/processor/git_open.go).
Use native Git's bounded history or an isolated exact object view when this
question must be answered; do not add a permanent compatibility analyzer.

SCC counting remains cheap and separate from diagnostic complexity. Unique-line
ratios are lexical, change coupling is co-change rather than import/effect
causality, and generated-file detection does not establish ownership. Duplicate
files must not disappear from budget accounting via `--no-duplicates`.

Current mutmut configuration targets only the verdict module. That is not broad
mutation assurance. The graph cache reports complete September 10 metadata, but
it indexes the accepted root, not these current worktree edits; its absence of
recorded issues cannot justify deletion. Serena inspected exact worktree owners.
The preceding full JUnit result places several refresh/closeout tests at 41–51
seconds; the affected proof module also spends 14–15 seconds in several setups.
Profile fixture/setup versus behavior before replacing scheduling or adding workers.

The useful loop is native measurement, source/relationship verification, a failing
counterexample, one owner repair or deletion, and an affected public-gate result.
The present repairs followed that loop: five real RED failures and 72 affected
GREEN tests. No global performance improvement or full current proof follows.
Receipts remain under the existing ignored evidence home as
`scc-capability-audit-20260913.json`, `scc-history-boundary-20260913.json` and
`authorized-reader-recovery-4dd2/`; their compact conclusions live here, not in a
second quality-policy or feedback database.

## Supply, Adoption, Knowledge And Learning

[in-toto statements][intoto-mechanism] and [DSSE envelopes][intoto-envelope] offer
subject/predicate and signed-envelope interchange. [SLSA tracks][slsa] distinguish
source and build assurances; [TUF][tuf] addresses trusted software updates; a
[CycloneDX SBOM][cyclonedx] describes supply contents. Reuse these boundaries where
cross-system consumers exist. Signatures and digests alone do not prove current
authority, independent verification or actual benefit. Standard adapters must
preserve the original Attestation identity and never create a second result owner.

[Copier's update mechanism][copier-mechanism] is a strong scaffold/upgrade candidate:
retain the template revision and answers, reapply user changes and surface
conflicts. Its generated candidate still requires ETHOS acceptance. Greenfield
can retain that upgrade basis from generation; brownfield must preserve native
layout and user customizations rather than pretend it was generated. Template
answers are generation provenance, not another intent store. Test deletion,
conflict, cancellation, upgrade and exit, including removal of owned hooks and
references without deleting user material.

[OKF 0.2][okf] is a knowledge-interchange research candidate, not a mandate to
restructure the repository. Its source/provenance/freshness relationships are
useful; its permissive unknown-field and broken-link handling cannot be copied
into trust-bearing admission. Optional index conventions do not justify adding
unnecessary index files. Export an accepted semantic view if a consumer needs it;
do not import a second intent, attestation or task system through documentation.
[Diataxis][diataxis] helps distinguish learning, practical guidance, explanation
and reference; it does not dictate a file-count rule or erase decision rationale.

Use native CLI/schema/API generation where it eliminates independently editable
copies. Verify meaning, not merely hashes or links. The architecture consumer's
R01–R14/P00–P09 report exposes a useful falsifier: current quality-contract lists
named obligations without definitions found in the inspected source surfaces.
Resolve the original owner/history; export necessary definitions or evidence-based
replacement mappings. G-series counts and rendered geometry cannot substitute
for undefined named criteria. This is a pending repair, not a concluded deletion.

[Inspect AI][inspect] and [DSPy][dspy] are candidates for evaluating and improving
replaceable interpretation/research capabilities. Preserve input sources, accepted
meaning, counterexamples and held-out workloads. Learned scores cannot compensate
for violated hard constraints, and observers cannot edit accepted criteria or
acquire write permission. A useful end-to-end result connects a deployed identity,
environment, baseline and observation window to the original objective; a green
build or successful deployment is not that result.

## Language And Product Shape

Python-only is not a product invariant. [Modern Python][python312] offers type
parameters, clearer type aliases and override checking; existing structured
concurrency and pattern matching can simplify implementations within the declared
support floor. New syntax must preserve generated schema and public behavior,
not merely reduce lines. Do not treat post-3.12 features as available on the
minimum supported interpreter.

[Rust][rust] is a candidate for a bounded packaging/process/filesystem or semantic
analysis component when its safety and deployment benefits beat boundary/build
costs. [Go][go] is a candidate for a standalone service/tool or direct CUE/CEL
integration when that removes more foreign-runtime machinery than it adds.
TypeScript may fit interactive interfaces and the tooling ecosystem without
moving authoritative meaning into a browser. [Rich][rich] and the existing CLI
framework can improve readable progress and diagnostics without creating another
command plane. No language migration is justified by shifting handwritten code
outside the Python budget; total maintenance surface remains visible.

## Comparative Acceptance Workload

This defines the missing comparison, not another roadmap. Execute through the
existing terminal plan and bounded official Changes; only one selected
production owner survives a successful comparison.

| Workload | Distinguishing observation |
| --- | --- |
| Pure decision and semantic extraction | Same legal/illegal/UNKNOWN verdicts under aliases, schema errors, policy changes and contradictory combined constraints. |
| Focused and complete verification | Cold, warm, one-source-change, one-rule-change, toolchain/environment-change and cleared-cache results agree; measure actual work avoided. |
| Native effects and cancellation | Real Git CAS, stale Lease, busy resources, timeout, child death and lost ACK; no repeated destructive effect or orphaned live resource. |
| Runtime preparation/activation | Exact immutable package, prior trust, offline supply, selector rollback, crash recovery and bounded cleanup on supported native platforms. |
| Reports and observability | Rebuild views without rerunning tests; preserve all attempts, source bindings, partial failure and redaction; measure added runtime/storage cost. |
| Collaboration and adoption | Greenfield and brownfield paths, handoff, cooperation with multiple contributions, zero/one winner, all-drop, useful-result preservation and conflict-aware upgrade/exit. |
| Delivery and actual outcome | Zero/one/multiple independent remotes, exact selected objects, partial publication and recovery; later observation can invalidate current evidence applicability without rewriting history. |

Record setup and execution separately; keep two test workers and fixed resource
limits for comparisons. Compare representative repetitions and report dispersion,
not a claimed speedup from one warm run. Before adoption, name deleted owner code,
configuration, subprocesses and manual maintenance touchpoints; count new runtime,
cache, trust and operational dependencies too. Do not fabricate a percentage
improvement threshold before measuring the baseline and agreeing the service need.

### Decision Disposition

- **Adopt now as design direction:** native/platform-first supporting mechanisms,
  one editable rule owner, typed observation coverage, complete input identities,
  bounded resource lifetimes, standard interoperable results and source-bound views.
- **Prioritize bounded trials:** native configured Git transport for the current
  handoff; Pants versus the existing native runner; Dagger for package/container
  work; mise versus Pixi supply ownership; CUE/CEL consolidation; Allure and
  OpenTelemetry over existing execution evidence; binding-aware semantic analysis.
- **Keep conditional:** durable orchestration, Cedar, WASI, formal solvers,
  additional implementation languages and external knowledge/protocol services.
  Each needs a concrete workload, removal target and conformance result.
- **Reject:** framework accumulation, parallel policy/workflow/intent authorities,
  claiming native-platform verification from containers, cache-as-authorization,
  report-as-proof, automatic acceptance of generated projections, and ELOC gaming.

No new runtime foundation is accepted by this report. The immediate handoff
remains unproven end to end; the next implementation must use these findings to
reduce its mechanism rather than convert this research into more scaffolding.

## Pinned Primary Sources

Links identify inspected documents, not blanket endorsements. Source-level and
README observations above have different strength; repository popularity and
marketing claims were not used as evidence of comparative performance.

[mise]: https://github.com/jdx/mise/blob/016fcd16a991c85e099d4f0b571bc44978a9eb94/docs/dev-tools/mise-lock.md
[mise-security]: https://github.com/jdx/mise/blob/016fcd16a991c85e099d4f0b571bc44978a9eb94/docs/security.md
[mise-cache]: https://github.com/jdx/mise/blob/016fcd16a991c85e099d4f0b571bc44978a9eb94/docs/tasks/caching.md
[pixi]: https://github.com/prefix-dev/pixi/blob/56ae6f39b887a954242002deeda5372f80b34a87/README.md
[uv]: https://github.com/astral-sh/uv/blob/8e70deb71b410d4bcf80fabdd88e8aa43a2e5878/README.md
[nix]: https://github.com/NixOS/nix/blob/203f85b2e851fc52e253e8e33eff5fb92936736a/README.md
[pants]: https://github.com/pantsbuild/pants/blob/c94f9f4ccfd43342b8f9379a139a328555bc5a5b/src/python/pants/engine/process.py
[dagger]: https://github.com/dagger/dagger/blob/f2aefc20cf41b5ed7922df7244e0f10ddc6031f7/README.md
[bazel]: https://github.com/bazelbuild/bazel/blob/aac8677f8e69e30fb105026ff524e04965640499/README.md
[git-hook]: https://github.com/git/git/blob/e9019fcafe0040228b8631c30f97ae1adb61bcdc/Documentation/git-hook.adoc
[git-hook-config]: https://github.com/git/git/blob/e9019fcafe0040228b8631c30f97ae1adb61bcdc/Documentation/config/hook.adoc
[git-ref]: https://github.com/git/git/blob/e9019fcafe0040228b8631c30f97ae1adb61bcdc/Documentation/git-update-ref.adoc
[pytransitions]: https://github.com/pytransitions/transitions/blob/bd42b38f3627e6bca7274fb4d9af2e105f75da7c/README.md
[scxml]: https://github.com/w3c/scxml/blob/360ce6f05d741987940ed7db01bc46b319102ad9/README.md
[xstate]: https://github.com/statelyai/docs/blob/54827bcf6591935ae1dc13484eafca88d3b4cf7a/content/docs/persistence.mdx
[anyio-mechanism]: https://github.com/agronholm/anyio/blob/4e72d8667818d4a972a549cd910a4e4340c504a0/docs/cancellation.rst
[cue]: https://github.com/cue-lang/cue/blob/e83d953917a564d12cf9a1cfcac5ecca9e8a711a/README.md
[cel]: https://github.com/google/cel-spec/blob/ba58ae5007845f3a1279b488cdeb79645ce958bb/README.md
[jsonschema]: https://github.com/json-schema-org/json-schema-spec/blob/4f56a9900674b27804f0ec32e3b7fdfa4efad695/README.md
[cedar]: https://github.com/cedar-policy/cedar/blob/2f4019fd645cc8d4a4c0c1f8bd0280c77d754e28/README.md
[cel-verifier]: https://github.com/cel-expr/cel-java/blob/33da350d02e2b14bc76f622fca2b9687c90c509a/verifier/README.md
[quint]: https://github.com/informalsystems/quint/blob/6fb2924e00707cef6dbc5e30db606d555c447123/README.md
[libcst-mechanism]: https://github.com/Instagram/LibCST/blob/d9a255843b5cdbecc6834684d233bce1f2987f9d/libcst/metadata/scope_provider.py
[tree-sitter]: https://github.com/tree-sitter/tree-sitter/blob/b2cf42f7ef45bbcbd527a4ea8ffdb9cc7b2b3500/README.md
[lsp]: https://github.com/microsoft/language-server-protocol/blob/3d9ba5d8e28ab7a577bb5aed1f27c166da0cb558/_specifications/lsp/3.17/specification.md
[scip]: https://github.com/sourcegraph/scip/blob/a279febaad96d05c8bc303c1bcaa11ebf348a82b/README.md
[codeql]: https://github.com/github/codeql/blob/cfc358e846dc1b26f4be2d1d2854c0d983c12ce8/README.md
[networkx]: https://github.com/networkx/networkx/blob/4e74880b0da01977da79915167c64e5c2af38b47/README.rst
[pluggy-mechanism]: https://github.com/pytest-dev/pluggy/blob/6a7f8960eb4009b551f14030233cea7a64ccaf5d/src/pluggy/_manager.py
[mcp]: https://github.com/modelcontextprotocol/modelcontextprotocol/blob/aa8ce049f089f92618340190d4ece141f663310d/README.md
[a2a]: https://github.com/a2aproject/A2A/blob/6d6640c29b102f7a8d23784901351b5d2454fe71/README.md
[wasmtime]: https://github.com/bytecodealliance/wasmtime/blob/2be5e3a62b9569bf3f46db996297a306442885ea/README.md
[hypothesis]: https://github.com/HypothesisWorks/hypothesis/blob/cd434f23be1a3598085cf096e28e6738c63b29b3/README.md
[allure3]: https://github.com/allure-framework/allure3/blob/e3bd84f644e1c58276a673f9d0ec546d2aba5855/README.md
[opentelemetry-mechanism]: https://github.com/open-telemetry/opentelemetry-specification/blob/5507eb587b3b3500ccd681e816e7c26729f38aa0/specification/overview.md
[cloudevents]: https://github.com/cloudevents/spec/blob/2ed3806b4ad8fda35813263cfefb2d73098b7655/cloudevents/spec.md
[intoto-mechanism]: https://github.com/in-toto/attestation/blob/2dcd055e9f72e746687c306e35f4e59720ff45be/spec/v1/statement.md
[slsa]: https://github.com/slsa-framework/slsa/blob/54b88b009fd45acb331c7e6578a526e0f36e0430/spec/tracks.md
[tuf]: https://github.com/theupdateframework/python-tuf/blob/d6b4392ea0620e2eae32f55bf317afd1009c0096/README.md
[cyclonedx]: https://github.com/CycloneDX/specification/blob/595d98f16159bdf7463adc140509ded479130b8b/README.md
[copier-mechanism]: https://github.com/copier-org/copier/blob/217e4f87828694df89e1513a1febdc33792f6e89/docs/updating.md
[okf]: https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/ad30107c31c06aec8a7d5636e0d1058118604e6f/SPEC.md
[diataxis]: https://github.com/evildmp/diataxis-documentation-framework/blob/957c09ca40b4a1edc23874f713e01937d50d54d5/README.rst
[inspect]: https://github.com/UKGovernmentBEIS/inspect_ai/blob/8ebe620d74c1eb679438db1b65324e30e2306092/README.md
[dspy]: https://github.com/stanfordnlp/dspy/blob/ecba33763316d2a4c6c756046a1118ecbff033e7/README.md
[python312]: https://github.com/python/cpython/blob/7bfa97f4dca58ab45def2ca0a1e8088997a4fa0b/Doc/whatsnew/3.12.rst
[rust]: https://github.com/rust-lang/rust/blob/9c99d05505bccb67912d68e05fe7fc7c58afcb41/README.md
[go]: https://github.com/golang/go/blob/fdcd66bb544d230a7eb0c2512e9e7a6ab191388b/README.md
[rich]: https://github.com/Textualize/rich/blob/9d8f9a372cc5916fd4781fec207ced7ddac2f08f/README.md
[temporal]: https://github.com/temporalio/sdk-python/blob/ab25ed693f7ec77589346e66c98db299a8c9c9fe/README.md
[pixi-environment]: https://github.com/prefix-dev/pixi/blob/56ae6f39b887a954242002deeda5372f80b34a87/docs/workspace/environment.md
[pants-process]: https://github.com/pantsbuild/pants/blob/c94f9f4ccfd43342b8f9379a139a328555bc5a5b/src/python/pants/engine/process.py
[intoto-envelope]: https://github.com/in-toto/attestation/blob/2dcd055e9f72e746687c306e35f4e59720ff45be/spec/v1/envelope.md

[openspec-customization]: https://github.com/Fission-AI/OpenSpec/blob/9d4e5974e5c0d9a09b9c6c1e1eb0975e80ec4461/docs/customization.md
