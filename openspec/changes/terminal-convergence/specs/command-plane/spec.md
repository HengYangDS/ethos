## MODIFIED Requirements

### Requirement: Public Command Plane
Commands SHALL project one mechanism: observe, extract, resolve, compile, evaluate, CAS apply, post-observe, attest, and project. Profiles may expose different views without creating another lifecycle engine.

#### Scenario: Cyclopts exposes the terminal root surface
- **WHEN** the root CLI help is rendered
- **THEN** it exposes exactly the six public commands
- **AND** `ethos status` is the single bounded reader
- **AND** maintainer mechanics remain hidden or semantically namespaced

#### Scenario: TransitionPlan is the single transition projection
- **WHEN** `ethos plan --json` compiles the current Commitment, repository
  facts, and declared nodes
- **THEN** it returns one deterministic `transition_plan`
- **AND** no parallel workflow-runtime or domain-contract read model is emitted

#### Scenario: Default payloads stay bounded
- **WHEN** `ethos status --json` or `ethos plan --json` would exceed its declared
  default payload budget
- **THEN** the command preserves `verdict`, `state`, `summary`, `required_gaps`,
  `next_action`, `continuation`, `missing_facts_or_evidence`, and
  `user_decision_required`
- **AND** oversized detail is replaced by a digest-bound artifact reference
- **AND** no alternate reader command or truth source is introduced

#### Scenario: a profile exposes status and plan
- **WHEN** a profile renders status and plan
- **THEN** both views derive from the same selected Commitment, fresh Facts, and TransitionPlan

#### Scenario: a reader derives continuation
- **WHEN** current authoritative facts are sufficient to select the next boundary
- **THEN** the schema-version-`2` result preserves `state` and `required_gaps`
  and exposes one `next_action`
- **AND** it derives exactly one `continuation`: `continue`, `await-user`,
  `blocked`, or `done`
- **AND** it exposes `missing_facts_or_evidence` from `required_gaps` only when
  `verdict=unknown`, and `user_decision_required` when judgment is required
- **AND** Continuation is recomputed rather than stored as lifecycle truth

#### Scenario: a complete adopter enters governed mutation
- **WHEN** a repository adopts ETHOS for material mutation
- **THEN** adoption initializes, pins, and verifies OpenSpec as its sole Change/SDD carrier
- **AND** `ethos status`, `ethos plan`, and `ethos prove` consume adapter
  observations without registering an `ethos openspec` public root
- **AND** a repository without verified OpenSpec remains observation-only and
  fails closed before governed mutation

#### Scenario: owner-native archive remains semantically namespaced
- **WHEN** a completed Work Lane Change must cross the archive boundary
- **THEN** the hidden lifecycle command is `ethos lane archive-change`
- **AND** no seventh public root, `ethos openspec` compatibility command, or
  parallel receipt authority is introduced
- **AND** installed CLI discovery and repository source expose the same command
  from the same package environment

### Requirement: Proof Command State Semantics
Verdicts SHALL be compact and truthful: `pass`, `block`, or `unknown`; missing or
unverifiable required facts produce `unknown` and block effects, while conflicts,
explicit failures, and warnings produce `block`. The public result envelope has no
top-level `ok` field.

#### Scenario: Planning proof is ready
- **WHEN** `ethos prove --json` completes without executing gates
- **THEN** the CLI reports `verdict=pass` and `state=ready` for successful readiness
- **AND** the CLI reports `executed=false`

#### Scenario: Executed proof is proven
- **WHEN** `ethos prove --execute --json` completes with all gates passing
- **THEN** the CLI reports `verdict=pass` and `state=proven`
- **AND** the CLI reports `executed=true`

#### Scenario: a required fact is unavailable
- **WHEN** a required observation cannot be verified
- **THEN** the command returns `unknown` and blocks the requested effect

## REMOVED Requirements

### Requirement: Explain Command Projects Invalid-State Signals

**Reason**: The retired `ethos explain` root and its separate taxonomy duplicate
the structured `required_gaps`, diagnostics, and singular `next_action` already
owned by each verifier and the schema-version-`2` result envelope.

**Migration**: Preserve each verifier's original signal and project its bounded
meaning and recovery directly through the six-command result contract.

**Replacement**: Public Command Plane

### Requirement: Self OpenSpec Lifecycle Mode

**Reason**: A carrier-specific public command creates a seventh workflow root
and embeds the ETHOS self profile in the generic product command plane.

**Migration**: The official OpenSpec CLI owns carrier validation and archival;
the six public ETHOS commands consume profile-adapter observations.

**Replacement**: Public Command Plane

### Requirement: ETHOS OpenSpec adapter remains under one command plane

**Reason**: Exposing `ethos openspec` makes an optional self-profile adapter a
public lifecycle owner.

**Migration**: Keep OpenSpec behind the selected profile adapter and report its
required facts through `status`, `plan`, and `prove`.

**Replacement**: Public Command Plane
