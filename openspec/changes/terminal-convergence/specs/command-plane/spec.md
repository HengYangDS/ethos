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

#### Scenario: the self profile selects OpenSpec
- **WHEN** the ETHOS self profile selects OpenSpec as its native intent carrier
- **THEN** the official OpenSpec CLI validates and archives that carrier
- **AND** `ethos status`, `ethos plan`, and `ethos prove` consume adapter
  observations without registering an `ethos openspec` public root
- **AND** an adopter selecting another native carrier requires no `openspec/`
  directory or OpenSpec installation

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

## REMOVED Requirements

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
