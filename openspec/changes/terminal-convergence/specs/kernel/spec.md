## ADDED Requirements

### Requirement: Minimal Terminal Semantic Kernel
ETHOS MUST persist only ChangeContract and Attestation as semantic entity types; RepositoryFacts MUST be re-observed and PlanIR MUST be transient, deterministic, hashable, and replayable.

#### Scenario: A repository change is compiled
- **WHEN** an effective ChangeContract and current RepositoryFacts are supplied
- **THEN** ETHOS produces a PlanIR containing only Check, Decision, and Effect nodes and does not require another semantic truth store

### Requirement: Closed Transition Verdict
Every required transition proposition MUST resolve to `pass`, `block`, or `unknown`; a missing or stale required proof MUST NOT resolve to pass.

#### Scenario: Required evidence cannot be verified
- **WHEN** a required attestation is absent, stale, malformed, or unavailable
- **THEN** the transition verdict is `unknown` or `block` and no mutating effect is admitted

### Requirement: Direct DAG Ordering
PlanIR ordering MUST use the standard-library graphlib implementation directly and MUST reject cycles before any effect.

#### Scenario: Plan dependencies contain a cycle
- **WHEN** the compiled PlanIR dependency graph is cyclic
- **THEN** planning blocks with a cycle diagnostic and executes zero effects

### Requirement: Singular Lifecycle Declaration
Lifecycle policy, lease operations, PlanIR actions, and campaign CEL MUST have
one strict declaration owner. Run state and execution checkpoints MUST remain
disposable substrate state rather than kernel entities.

#### Scenario: Lifecycle policy is loaded
- **WHEN** ETHOS loads the product lifecycle declaration
- **THEN** the declaration validates against one language-neutral schema
- **AND** no workflow-run schema, runtime read model, or parallel transition
  registry is required

### Requirement: Current Facts Exclude Historical Ledgers
RuleFactSnapshot and PlanIR MUST derive current verdicts from Git, worktree,
OpenSpec, host readiness, policy, and projection facts. Historical claims and
Chronicle records MAY remain immutable evidence but MUST NOT be required current
facts. A parallel command registry MUST NOT exist.

#### Scenario: A historical claim or registry projection is stale
- **WHEN** current repository facts and the ChangeContract are valid
- **THEN** the historical projection does not block planning or proof
- **AND** it cannot make a blocked current transition pass
