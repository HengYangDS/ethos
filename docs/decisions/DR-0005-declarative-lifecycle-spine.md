---
subject: ethos:decision:declarative-lifecycle-spine
role: decision
state: canonical
relations:
  canonical_for: declarative lifecycle spine
  informs:
    - docs/architecture/declarative-governance-compiler.md
    - docs/architecture/transition-plan.md
    - docs/plans/terminal-governance-product-design.md
---

# DR-0005: Declarative Lifecycle Spine

Status: accepted.

Purpose: establish the singular declaration-first lifecycle spine for ETHOS
without ceding repository truth or lifecycle authority to a framework.

See also: [Decision Records](README.md), [Decision Index](decision-index.md),
[Declarative Governance Compiler](../architecture/declarative-governance-compiler.md),
[TransitionPlan](../architecture/transition-plan.md), and
[Terminal Governance Product Design](../plans/terminal-governance-product-design.md).

## Record

| Field | Value |
| --- | --- |
| Decision ID | DR-0005 |
| Kind | architecture |
| Decision Makers | ETHOS maintainer and authorized work lane |
| Status | accepted |
| Decision Date | 2026-07-10 |
| Decision Version | 5 |
| Decision Change Date | 2026-08-07 |
| Record Review Date | 2026-10-10 |
| Supersedes | None |
| Superseded By | None |
| Depends On | None |
| Scope | Contract models, policy evaluation, TransitionPlan, CLI composition, serialization, projections, and anti-regression gates. |
| Boundary | ETHOS owns repository truth and transition semantics; frameworks and tools provide replaceable mechanisms only. |
| Decision | Use OpenSpec and typed repository declarations as declarative frontends, pure deterministic compilation into TransitionPlan as the typed IR, CEL only for bounded side-effect-free predicates, one native effect interpreter, and post-observation Attestations. Compile adaptive review and zero-or-more Skill capabilities from current facts; no DSL, Skill, workflow, plugin, or model response executes effects. ETHOS is the vendor-neutral semantic control plane for autonomous software engineering; its Python package is one reference distribution over language-neutral contracts and governed extensions. |
| Consequences | Public contracts, rules, commands, projections, and plans are declaration-first. Python remains for pure compilation or explicit I/O and mutation adapters. Parallel registries, graph wrappers, compatibility layers, DI containers, and in-process event buses are not admitted without unique semantics and measured net benefit. |
| Proof or Evidence | The `terminal-convergence` OpenSpec change owns implementation and deletion proof; focused contract, determinism, schema, command, and HEAD-bound proof must pass before closeout. |
| Revisit Trigger | Revisit when declarations increase total maintenance, obscure authority, prevent explanation, or require an execution substrate to own lifecycle truth. |

## Context

ETHOS had accumulated procedural gap collection, dictionary normalization,
hand-written command glue, repeated dependency walkers, and generated surfaces
with overlapping ownership. The corrective principle is not “replace Python
with frameworks.” It is one semantic obligation, one owner, and the smallest
mature mechanism that preserves meaning.

## Decision

Use the following singular lifecycle spine:

1. **Contracts:** Pydantic v2 only at persisted or external boundaries.
2. **Facts:** freshly observed and passed explicitly; no ambient mutable truth.
3. **Rules:** declarations first, CEL only for predicates that need a terminating,
   side-effect-free expression language, and one selected CEL implementation
   after parity. CEL does not own workflow, effects, or repository state.
4. **Plans:** pure compilers map the selected Commitment, current Facts, policy,
   and prior Attestations into `TransitionPlan`, which contains `Check`,
   `Decision`, and `Effect` nodes; Python
   `graphlib` directly supplies cycle detection and topological order.
5. **Commands:** Cyclopts declarations own the command surface; documentation,
   schemas, and protocol metadata are derived rather than separately registered.
6. **Effects:** adapters execute admitted operations with explicit roots,
   permissions, expected state, and compare-and-swap preconditions.
7. **Evidence:** execution returns immutable attestations instead of publishing
   hidden events or mutating a second truth store.
8. **Review:** workload and risk facts compile a deterministic-first set of
   pre-implementation and post-implementation lenses. Repairable findings are
   fixed and recompiled by the agent; humans resolve only irreducible intent,
   trust, irreversible-effect, and final product choices.
9. **Skills:** operation and repository facts compile zero or more required
   capabilities. Host Skills and slash commands are projections; repository
   enforcement remains authoritative when an agent ignores them.
10. **Ecosystem:** a stable minimal kernel and language-neutral conformance
    contract support independently distributed schemas, method packs, review
    lenses, Skills, plugins, agent hosts, protocol adapters, provider adapters,
    and adopter tooling. Discovery, versioning, provenance, isolation, demand
    loading, and uninstall are contract properties rather than package-local glue.
11. **Agentic position:** model providers, agent SDKs, harnesses, IDE clients,
    sandboxes, and multi-agent runtimes own inference, turns, sessions, tool
    invocation, delegation, and presentation. MCP owns context/tool transport,
    A2A owns opaque agent interoperability, and ACP owns editor-agent transport.
    ETHOS owns the repository-scoped continuity those layers do not: selected
    intent, capability and permission compilation, exact transition authority,
    durable evidence, recovery, and conformance across host or protocol changes.
    OpenTelemetry traces are disposable observations; SLSA/in-toto/Sigstore may
    carry publication provenance, but none becomes repository truth or a second
    lifecycle owner.

Execution runtimes, workflow engines, policy servers, graph frameworks,
state-machine frameworks, DI containers, and event buses remain outside the
kernel. They may become optional adapters only after a real consumer proves
that the existing contracts and adapter protocol cannot express the requirement
more simply. CUE and OPA/Rego remain measured destructive-replacement candidates,
not additive policy layers: CUE must replace schema/configuration validation, and
OPA/Rego must replace a materially larger decision surface than CEL without an
online policy service or second effect path. An admitted tool is used through its
applicable official model and extension surfaces; ETHOS does not retain hand-made
substitutes merely to minimize dependency use.

## Proof

Completion requires:

- contract and JSON Schema conformance;
- deterministic TransitionPlan digest, ordering, cycle, and replay properties;
- CEL parity before deleting the incumbent predicate path;
- deterministic replay of declaration-to-TransitionPlan compilation and a
  negative proof that predicates and Skills cannot execute effects;
- adaptive review coverage from requirements through code, tests, evidence, and
  reverse-discovered behavior;
- multi-skill activation and host-noncompliance rejection at repository-native
  enforcement boundaries;
- ecosystem capability discovery, conformance, version, provenance, isolation,
  demand-loading, and clean-uninstall proof independent of the Python package;
- the same accepted intent, permission boundary, verdict, effect identity, and
  Attestation survive a change of model, agent runtime, host, and protocol;
- one Cyclopts-owned command surface with projection drift checks;
- zero production graph wrappers or parallel command registries;
- terminal source budgets and a HEAD-bound complete proof.

## Invariants

- Repository truth and transition authority remain in ETHOS contracts.
- Every semantic obligation has one owner.
- Persisted models, CLI, predicates, DAG ordering, effects, and schemas each have one mechanism.
- A framework is admitted only for irreducible semantics and measured net benefit.

## Alternatives Considered

| Option | Verdict | Pros | Cons | Decision basis |
| --- | --- | --- | --- | --- |
| Strict boundary models plus direct mature mechanisms | selected | Uses Pydantic v2, CEL, `graphlib`, Cyclopts, and JSON Schema without wrapping them in parallel owners. | Requires strict parity, drift, determinism, and deletion proof. | It maximizes mature capability reuse while preserving one semantic owner. |
| attrs, dataclass, and Pydantic dual models | rejected | Reduces local migration friction. | Creates conversion code, duplicate contracts, and duplicated tests. | It violates singular persisted-contract ownership. |
| Custom graph layer or a rich graph framework in the kernel | rejected | Offers broader graph analytics. | TransitionPlan needs only ordering and cycle detection; a wrapper becomes a second owner. | Direct `graphlib.TopologicalSorter` is sufficient for kernel semantics. |
| DI container, event bus, or workflow runtime as the product center | rejected | Provides generic composition and orchestration abstractions. | Obscures dependencies and risks creating another lifecycle truth plane. | Explicit arguments, TransitionPlan, and Attestations already carry the required meaning. |
| CUE as an additional configuration language | rejected pending destructive proof | Unifies constraints, validation, and generation. | Adds a Go runtime and second schema language while Pydantic/TOML remain active. | Admit only if an offline portable cutover removes more validation and projection code than it adds. |
| OPA/Rego beside CEL | rejected pending destructive proof | Expresses rich decisions and partial evaluation. | Adds a second policy language, bundle/runtime surface, and possible service topology. | Admit only for a real cross-language consumer that deletes the incumbent decision owner and remains offline. |
| Fixed human approval before and after coding | rejected | Easy to explain and mirrors familiar stage gates. | Raises human cognitive cost, delays safe low-risk work, and does not prove semantic review quality. | Compile risk-based independent review lenses; escalate only irreducible decisions and final judgment. |
| Treat ETHOS as only a Python package | rejected | Simplifies packaging and implementation scope. | Makes CLI internals the ecosystem boundary and forces every extension to couple to Python. | The package is a reference distribution; protocols, schemas, conformance, and governed capabilities define the ecosystem. |
| Turn ETHOS into an agent harness or multi-agent runtime | rejected | Could own turns, sessions, delegation, tools, sandboxes, and tracing in one product. | Competes with rapidly evolving host runtimes, couples governance to model execution, and duplicates session state. | ETHOS governs the durable repository transition across runtimes; it does not own the reasoning loop. |
| Invent ETHOS-native tool, agent, or editor protocols | rejected | Gives complete control over transport and discovery. | Duplicates MCP, A2A, and ACP and makes every integration bespoke. | Implement thin conformant projections and keep protocol fields outside the semantic kernel. |

## Selected Approach And Rationale

Use one mature mechanism directly for each irreducible concern and keep the
implementation centered on pure compilation plus explicit effects.

## Consequences

The selected stack is destructive: dual models, graph wrappers, command
registries, service locators, and event buses must be deleted rather than kept
as compatibility layers.

## Proof Or Evidence

- Contract/schema conformance.
- CEL parity, TransitionPlan determinism/cycle tests, and Cyclopts surface tests.
- Terminal source-budget and exact-HEAD proof.

## Revisit Trigger

Reopen when a real consumer proves the selected mechanisms cannot express an
irreducible requirement without semantic loss.

## Decision Change Ledger

| Version | Date | Change | Reason | Evidence |
| --- | --- | --- | --- | --- |
| 3 | 2026-07-26 | Selected the declaration-first terminal stack | Remove procedural and framework duplication | Terminal design and focused gates |
| 4 | 2026-07-28 | Added explicit alternatives and deletion consequences | Prevent reintroduction of parallel mechanisms | Terminal-convergence decision discipline |
| 5 | 2026-08-07 | Defined the typed functional spine, adaptive review, multi-skill activation, ecosystem boundary, and CUE/Rego replacement bar | Convert SDD, DSL, review, and ecosystem research into enforceable owner semantics | Official OpenSpec, CEL, CUE, OPA, Spec Kit, AI-DLC, SpecD, BMAD, Agent OS, and Tessl mechanism review |
