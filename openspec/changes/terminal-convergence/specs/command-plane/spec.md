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
- **THEN** the command preserves verdict, summary, required gaps, and next actions
- **AND** oversized detail is replaced by a digest-bound artifact reference
- **AND** no alternate reader command or truth source is introduced

#### Scenario: a profile exposes status and plan
- **WHEN** a profile renders status and plan
- **THEN** both views derive from the same selected Commitment, fresh Facts, and TransitionPlan

### Requirement: Proof Command State Semantics
Verdicts SHALL be compact and truthful: `pass`, `block`, or `unknown`; unknown required facts block effects.

#### Scenario: Planning proof is ready
- **WHEN** `ethos prove --json` completes without executing gates
- **THEN** the CLI reports `ok=true` and `state=ready` for successful readiness
- **AND** the CLI reports `executed=false`

#### Scenario: Executed proof is proven
- **WHEN** `ethos prove --execute --json` completes with all gates passing
- **THEN** the CLI reports `ok=true` and `state=proven`
- **AND** the CLI reports `executed=true`

#### Scenario: a required fact is unavailable
- **WHEN** a required observation cannot be verified
- **THEN** the command returns `unknown` and blocks the requested effect

### Requirement: ETHOS OpenSpec adapter remains under one command plane
Native carriers SHALL be profile-selected. OpenSpec is optional for ETHOS self-governance and SHALL not be a generic adopter prerequisite.

#### Scenario: OpenSpec adapter composes official and ETHOS checks
- **WHEN** `ethos openspec --lifecycle --json` runs
- **THEN** the payload includes official OpenSpec doctor, status, and strict
  validation results
- **AND** it includes ETHOS lifecycle carrier review for proposal, design,
  tasks, delta specs, capability profiles, Commitment validity, evidence refs, and
  live-spec diff guards

#### Scenario: OpenSpec adapter does not become a second public command plane
- **WHEN** ETHOS reports OpenSpec governance gaps
- **THEN** the next action enters through an `ethos ...` command
- **AND** raw OpenSpec CLI commands remain adapter implementation detail or
  maintainer reference rather than the adopter first-hour workflow

#### Scenario: Lifecycle semantics use OpenSpec as carrier
- **WHEN** lifecycle or transition semantics are changed
- **THEN** an OpenSpec change carrier records the intent and deltas
- **AND** official OpenSpec validation remains carrier validation rather than runtime authority

#### Scenario: an adopter has no OpenSpec directory
- **WHEN** an adopter selects another native carrier
- **THEN** it can compile and prove a transition without an `openspec/` directory
