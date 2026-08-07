## MODIFIED Requirements

### Requirement: One Owner Per Property
Each quality property SHALL have one admitted owner consumed identically by local and hosted execution.

#### Scenario: Two tools claim the same property

- **WHEN** the tracked tool, gate, and owner-script declarations are audited
- **THEN** the overlap is a required gap unless one tool is explicitly a bounded
  pilot replacing the other
- **AND** a baseline, hosted dashboard, or convenience wrapper cannot become a
  second authority

#### Scenario: duplicate quality implementations exist
- **WHEN** two owners claim the same quality property
- **THEN** admission blocks until one owner is selected and the other is removed

#### Scenario: a built-artifact SBOM is required

- **WHEN** local or hosted release packaging completes one Python wheel
- **THEN** the single SBOM owner is pinned Syft emitting SPDX 2.3 JSON for that
  exact artifact
- **AND** the native SPDX-lite builder, recursive envelope runner, and shaped
  in-toto or SLSA claims are absent
- **AND** provenance and signatures remain unknown until provider-native receipts
  bind the same artifact digest.

#### Scenario: a quality owner runs against a repository checkout
- **WHEN** any product-owned status, admission, gate, or proof implementation runs
- **THEN** runner source, schema source, editor root, audit root, and target checkout
  resolve to the same Git worktree
- **AND** a PATH executable, global installation, accepted-root package, or stale
  environment cannot substitute for that checkout's source or schema

#### Scenario: a selected mature capability is accepted
- **WHEN** Pydantic v2, Cyclopts, `graphlib.TopologicalSorter`, or the selected CEL
  engine is added, upgraded, or retained for its declared property
- **THEN** focused acceptance proves boundary validation, CLI binding, DAG
  ordering, or predicate evaluation respectively
- **AND** dependency and lock agreement, vulnerability posture, required offline
  operation, deterministic behavior, clean uninstall, and net deletion pass
- **AND** imports, schemas, CLI declarations, and lock metadata name the same
  selected implementation
- **AND** no wrapper framework, dual model, graph abstraction, expression
  fallback, or compatibility layer shares ownership

#### Scenario: the selected capability fails acceptance
- **WHEN** it cannot satisfy security, lock, uninstall, determinism, consumer, or
  net-deletion criteria
- **THEN** the change blocks or removes it rather than retaining a speculative
  framework owner or parallel fallback

### Requirement: Warning And Suppression Zero
Warnings, suppressions, stale projections, and unknown required facts SHALL fail closed; no passing verdict coexists with them.

#### Scenario: A command succeeds with a warning

- **WHEN** a governed quality command exits zero but emits an unapproved warning
- **THEN** its gate fails
- **AND** the warning must be removed or represented by an explicit bounded
  decision with a deletion condition

#### Scenario: Production contains a suppression

- **WHEN** quality proof finds `fmt off/on`, `noqa`, type-ignore, coverage-ignore,
  or an equivalent suppression in production source
- **THEN** proof blocks until the construct is deleted or replaced by a truthful
  semantic layout

#### Scenario: a CI warning is emitted
- **WHEN** a required quality command emits a warning
- **THEN** the quality verdict blocks rather than reporting pass

### Requirement: Native Carrier Quality
Quality SHALL preserve each carrier's native syntax and owner rather than mechanically rewriting prose or inventing a universal format.

#### Scenario: A carrier is checked

- **WHEN** config, docs, shell, or format proof runs
- **THEN** deterministic format, syntax, schema, links, anchors, and shell safety
  are checked by the declared native owner
- **AND** the gate does not rewrite governed content during proof

#### Scenario: a provider workflow is exercised locally
- **WHEN** locked `act` or the declared GitLab emulator executes a provider projection
- **THEN** it consumes the same owner scripts and portable gate declarations as hosted CI
- **AND** its result is local evidence only and cannot substitute for a GitHub or GitLab hosted Attestation

#### Scenario: an orchestration or environment tool is proposed
- **WHEN** Tox, Nox, Pixi, Pants, Dagger, or another workflow substrate is proposed
- **THEN** admission requires a real consumer, a distinct owned property, offline lock reproducibility, clean uninstall, and measured net deletion of current scripts, declarations, and dependencies
- **AND** a second task runner, environment matrix, pipeline language, policy owner, or convenience wrapper is rejected

#### Scenario: Python product or contributor execution starts
- **WHEN** a local, CI, SDK, build, test, or ETHOS command requires Python
- **THEN** it resolves the current worktree, matching `pyproject.toml`, `uv.lock`,
  project `.venv`, and source before execution
- **AND** Nox reuses that locked environment and owns reusable sessions while
  Hatchling alone owns package builds
- **AND** global executables, system site-packages, implicit PATH fallback, and a
  second tool-created virtual environment fail closed
- **AND** Nox replaces subsumed shell orchestration rather than wrapping it

#### Scenario: a generated artifact drifts
- **WHEN** a declared projection differs from its source binding
- **THEN** the owning drift check blocks the stale artifact

### Requirement: Terminal Compression And Test Floor
Terminal proof SHALL enforce Python effective LOC at or below 54,000, global
owned-source effective LOC at or below 68,000, branch coverage at or above 95
percent, and complete behavior coverage for authority, CAS, and pure transition
reducers. Intermediate campaign growth SHALL be allowed only when the same
campaign retains a proved net-deletion path.

#### Scenario: semantics move between carriers
- **WHEN** executable behavior moves among source, tests, tools, configuration,
  templates, or generated owned source
- **THEN** global measurement continues to count it and grants no false deletion credit.

#### Scenario: changed scope is admitted against a baseline
- **WHEN** a change requests source-budget admission
- **THEN** the owner resolves the exact merge base from the declared baseline and
  current HEAD before measuring the changed scope
- **AND** every coordinate is evaluated independently against its own baseline,
  limit, and changed paths
- **AND** savings in one coordinate, carrier shift, generated displacement, or a
  below-limit aggregate cannot compensate for growth or a breach in another
  coordinate

#### Scenario: coverage is raised without behavioral proof
- **WHEN** a test reaches a branch without asserting the required behavior
- **THEN** it does not satisfy the capability or critical-owner coverage floor.

#### Scenario: repository-wide quality executes
- **WHEN** terminal quality proof runs
- **THEN** it covers source, tests, tools, configuration, schemas, documentation,
  links including external links, CI, forge templates, records, and generated projections
- **AND** Cyclopts is the only CLI framework, production `__all__`, import aliases,
  thin forwarding modules, re-exports, compatibility wrappers, ambiguous module
  names, duplicate definitions, dead code, and unowned suppressions are absent
  unless a narrow semantic owner proves necessity.

#### Scenario: a reducer enters bounded mutation testing
- **WHEN** fault seeding can falsify an authority, exact-CAS, permission,
  deterministic-serialization, or closed-verdict invariant in a pure reducer
- **THEN** the mutation owner selects the exact module, mutation operators,
  behavioral tests, time budget, and minimum kill criteria
- **AND** surviving in-scope mutants block until the behavior or declared
  equivalent-mutant judgment is proved
- **AND** timeout, infrastructure failure, or unclassified survivor is `unknown`,
  never pass
- **AND** mutation testing does not become a repository-wide score, permanent
  duplicate test runner, or justification for coverage-only tests

#### Scenario: mutation testing has no distinct signal
- **WHEN** a candidate scope duplicates branch coverage, targets effects or
  adapters that cannot run deterministically, or fails to find a killable
  representative mutant within its pilot budget
- **THEN** the scope is rejected or retired without adding another framework
  owner, baseline, wrapper, or advisory score

### Requirement: Matched Workflow Evaluation
Execution methods SHALL be compared as evidence over matched tasks rather than
accepted through self-reported speed or quality claims.

#### Scenario: an execution method is evaluated
- **WHEN** ETHOS compares a host, model tier, method pack, runtime, or external operator
- **THEN** the protocol uses task × treatment × repetition with explicit
  control/candidate assignment, Pass@k, Pass^k, and polluted-sample exclusion
- **AND** it records completion, token use, wall time, turns, recovery success,
  intent omission, invalid mutation, duplicate implementation, terminal ELOC,
  and evidence completeness
- **AND** evaluation results remain evidence and cannot directly mark tasks done,
  authorize land or publish, or become another progress store

#### Scenario: a pre-implementation review set is compiled
- **WHEN** proposal, specs, design, and tasks are ready for implementation
- **THEN** ETHOS derives the required review lenses from workload kind, affected
  capabilities, ambiguity, risk, architecture, security, migration,
  reversibility, and current repository facts
- **AND** deterministic structure, traceability, contradiction, and policy checks
  run before judgment-heavy lenses
- **AND** unresolved intent or mutually valid product choices produce
  `await-user`, while repairable findings return one agent-executable next action

#### Scenario: completed implementation is reviewed against intent
- **WHEN** implementation and focused tests complete
- **THEN** review binds each requirement and scenario to implementation, tests,
  evidence, and changed paths, and searches changed behavior for requirements
  absent from the selected Change
- **AND** missing realization, stale specs, undocumented behavior, failing tests,
  architecture or security drift, and incomplete evidence block completion
- **AND** the agent repairs clear findings and recompiles the review set before
  escalating only unresolved intent, trust, or irreversible decisions to a human

#### Scenario: a policy or DSL runtime is proposed
- **WHEN** CUE, OPA/Rego, another expression language, state-machine framework,
  or workflow engine is proposed
- **THEN** matched evaluation names the exact hand-written validators, compilers,
  branches, schemas, or projections it replaces and measures terminal net deletion
- **AND** a candidate that adds a second policy language, effect path, state
  store, workflow authority, online service, or non-portable runtime is rejected
- **AND** CEL remains limited to bounded side-effect-free predicates and no DSL
  directly executes effects

### Requirement: Product Experience Is A Kernel Projection
CLI, Python SDK, language-neutral conformance assets, optional MCP/A2A adapters,
and CI/forge integrations SHALL project one semantic result and SHALL NOT create
parallel policy, lifecycle, error, or truth ownership.

#### Scenario: a human or machine receives a non-pass result
- **WHEN** current facts produce `block` or `unknown`
- **THEN** every surface preserves the same stable diagnostic code, verdict,
  evidence boundary, missing fact or blocker, singular safe next action, and
  user-decision requirement
- **AND** human output explains it concisely while JSON remains schema-stable
- **AND** no surface hides the gap, substitutes generic advice, or offers several
  semantically equivalent next commands

#### Scenario: a repository is adopted or uninstalled
- **WHEN** a user previews, applies, repeats, or removes adoption
- **THEN** preview is side-effect free, apply is idempotent and minimally invasive,
  and uninstall removes product-owned hooks and projections without deleting
  native repository state
- **AND** complete mutation adoption verifies OpenSpec while observation-only use
  remains explicit and non-mutating

#### Scenario: a product surface is implemented
- **WHEN** CLI, SDK, MCP/A2A, CI, forge, or generated scaffold behavior is added
- **THEN** it consumes the typed application service and shared conformance cases
- **AND** transport-specific code contains no duplicate compiler, policy evaluator,
  durable session state, task progress, or error taxonomy
