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
