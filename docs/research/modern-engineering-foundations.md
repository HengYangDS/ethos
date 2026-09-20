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

## Read By Question

The overview owns the comparative frame and acceptance workload. Each topic
owns its detailed alternatives, observations and source references; topic pages
do not create another product contract or execution plan. Dated observations
are not present-tense completion claims.

| Question | Topic |
| --- | --- |
| Who selects tools, locks dependencies and prepares environments? | [Toolchain and supply](foundations/toolchain.md) |
| What should run natively or in containers, and what may be reused? | [Execution and reuse](foundations/execution.md) |
| What do state machines, hooks and durable engines actually guarantee? | [Effects and recovery](foundations/effects.md) |
| What distinguishes configuration validity from program meaning? | [Executable semantics](foundations/semantics.md) |
| How do tests, Allure reports and telemetry support useful evidence? | [Verification and observability](foundations/verification.md) |
| How are intent, adoption, updates and actual benefit preserved? | [Intent and adoption](foundations/adoption.md) |
| Where do SDK/MCP, plugins and different languages belong? | [Interfaces and extensions](foundations/interfaces.md) |
| How can people and agents navigate one reliable knowledge source? | [Documentation and knowledge interchange](foundations/documentation.md) |

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

Record setup and execution separately; hold worker counts fixed within each
implementation comparison and separately qualify faster concurrency. Keep resource
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
