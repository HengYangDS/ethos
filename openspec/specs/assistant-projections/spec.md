# ETHOS Assistant Projections

## Purpose

ETHOS SHALL expose assistant, MCP, ACP, context, and repo-local skills as thin
projections over repository truth.

## Requirements

### Requirement: Projection Boundary

ETHOS SHALL keep assistant, MCP, ACP, hosted CI, workflow runtimes, external
agent hosts, and provider-visible skill packages as adapters, method packs,
context providers, or projections over repository truth.

#### Scenario: projection drift is audited

- **WHEN** `ethos prove --gate skills --json` runs
- **THEN** it reports package and registry drift without accepting host metadata as authority

### Requirement: Progressive disclosure for agent context

Agent context SHALL be a thin entrypoint over current machine facts: observe,
interpret the schema-versioned result, follow singular next_action/continuation,
and expand only into relevant rule, skill, design, OpenSpec or evidence owners.
The entrypoint SHALL NOT duplicate a fixed lifecycle, task ledger, authority
order or detailed procedure. Neither entrypoints nor skills grant mutation
admission.

#### Scenario: Agent loads minimal context first

- **WHEN** an agent starts work in a governed repository
- **THEN** the first loaded surface identifies the repository-local authority
  boundary and directs the agent to the current status result
- **AND** detailed operating semantics remain in their task-specific owners
  rather than the entrypoint

#### Scenario: Current result selects the continuation

- **WHEN** the current ETHOS result exposes `verdict`, `required_gaps`, singular
  `next_action`, `continuation`, and `user_decision_required`
- **THEN** the agent follows that result instead of executing a hard-coded
  command sequence or inferring a lifecycle from prose
- **AND** a blocked or unknown result is not converted into authorization

#### Scenario: Agent expands by task need

- **WHEN** the current result or changed scope identifies a task-specific rule
  or skill route
- **THEN** the agent loads only that rule or skill and its direct references
- **AND** avoids bulk-loading unrelated docs, archives, generated artifacts,
  evidence, or host projections

#### Scenario: Tracked mutation uses current admission

- **WHEN** an agent is ready to change tracked files
- **THEN** it enters an owned Work Lane and obtains a passing current
  `ethos lane prewrite` decision for the exact target root and paths
- **AND** neither the entrypoint nor a skill grants write authority

### Requirement: Agent projections preserve native Change ownership

OpenSpec SHALL alone own Change intent, design, specs and progress. Commitment
SHALL remain transient; skills SHALL remain optional projections. ETHOS SHALL
NOT retain a skill that owns or redescribes the native Change lifecycle. Public
ETHOS commands SHALL remain independent capabilities selected by current results,
not a sequence owned by an agent projection.

#### Scenario: Change lifecycle retains one owner

- **WHEN** the repository exposes agent skills and public ETHOS commands
- **THEN** OpenSpec remains the sole owner of Change authoring, progress,
  validation, and archive
- **AND** no ETHOS skill or current document reifies the public command catalog
  as a second Change lifecycle

#### Scenario: Official Change planning remains writable

- **WHEN** one active official Change has generated some but not all of its
  declared planning artifacts and a partial Commitment is already compilable
- **THEN** prewrite admits only the still-declared official artifact outputs
  needed to complete that Change
- **AND** the partial Commitment does not turn incomplete planning into a
  self-blocking state or authorize unrelated product paths

### Requirement: Skill surfaces remain projections over repository truth
ETHOS SHALL keep repo-local skills as concise procedures over source, tests,
schemas, docs, OpenSpec, rules, and evidence rather than independent truth
stores.

#### Scenario: Host skill roots are not canonical
- **WHEN** a host-native skill directory exists
- **THEN** ETHOS treats it as a projection unless a declared host-native
  artifact contract says otherwise
- **AND** canonical repository skill work belongs in the declared skill source
  for the terminal design

### Requirement: Terminal assistant projections are derived, not root configuration

ETHOS SHALL derive assistant and host projections from repository source,
activation registries, declared surfaces, and schemas, and SHALL NOT require or
scaffold a root `.ethos/assistants.toml` truth file.

#### Scenario: A repository is scaffolded or parity-checked

- **WHEN** ETHOS renders the current adopter scaffold or checks its manifest
- **THEN** `.ethos/assistants.toml` is absent from required artifacts
- **AND** assistant projection behavior continues to come from canonical source
  and activation contracts.

#### Scenario: The product removes the retired projection file

- **WHEN** the product checkout no longer contains `.ethos/assistants.toml`
- **THEN** projection checks and assistant tests remain valid
- **AND** no runtime consumer treats the removed file as required truth.

### Requirement: Skill portfolio validation

ETHOS SHALL expose repo-local skill portfolio validation through the stable
`skills` gate. One skill owner SHALL validate original activation inputs,
package quality, routing, composition and retirement, then project explicit
verdicts and gaps. Skills remain below repository truth.

#### Scenario: Skills are checked through one owner

- **WHEN** `ethos prove --gate skills --json` runs
- **THEN** it uses the same portfolio owner as repository audit and planning
- **AND** the report has no development-generation mode or duplicate compliance score

#### Scenario: Placeholder and weak entrypoint are rejected

- **WHEN** a skill lacks required content or a usable trigger and entrypoint
- **THEN** the report retains precise package-quality failures

#### Scenario: Overlapping route owners are rejected

- **WHEN** active skills declare conflicting routes or duplicate primary owners
- **THEN** the report identifies those conflicts without granting skill authority

#### Scenario: Missing portfolio coverage is reported

- **WHEN** declared required primary subjects have no active owner
- **THEN** the report exposes missing coverage and the exact owner map

#### Scenario: Unsupported activation remains invalid

- **WHEN** old or future activation input does not satisfy the supported schema
- **THEN** the original input is rejected rather than normalized into compatibility

#### Scenario: Skill evaluation metadata remains evidence

- **WHEN** a package declares evaluation metrics, treatment identity and evidence references
- **THEN** the same package owner validates them without converting them into task progress
