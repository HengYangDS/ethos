## MODIFIED Requirements

### Requirement: Progressive disclosure for agent context

ETHOS SHALL structure agent-facing documentation as a thin repository
entrypoint over current machine facts. The entrypoint SHALL direct an agent to
observe the repository, interpret the schema-versioned result, follow its
singular `next_action` according to `continuation`, and expand only into the
task-relevant rule, skill, design, OpenSpec, or evidence owner.

The entrypoint SHALL NOT reproduce a fixed lifecycle, task ledger, authority
order, or detailed operating procedure. OpenSpec remains the sole Change,
design, specification, and task-progress carrier; Commitment remains a
transient acceptance compilation; and skills remain optional procedural
projections.

ETHOS SHALL NOT retain a repository skill that owns or re-describes the native
OpenSpec Change lifecycle. Public ETHOS commands remain independently
addressable capabilities selected by the current result rather than a sequence
owned by an agent projection.

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

#### Scenario: Change lifecycle retains one owner

- **WHEN** the repository exposes agent skills and public ETHOS commands
- **THEN** OpenSpec remains the sole owner of Change authoring, progress,
  validation, and archive
- **AND** no ETHOS skill or current document reifies the public command catalog
  as a second Change lifecycle

#### Scenario: Tracked mutation uses current admission

- **WHEN** an agent is ready to change tracked files
- **THEN** it enters an owned Work Lane and obtains a passing current
  `ethos lane prewrite` decision for the exact target root and paths
- **AND** neither the entrypoint nor a skill grants write authority

#### Scenario: Official Change planning remains writable

- **WHEN** one active official Change has generated some but not all of its
  declared planning artifacts and a partial Commitment is already compilable
- **THEN** prewrite admits only the still-declared official artifact outputs
  needed to complete that Change
- **AND** the partial Commitment does not turn incomplete planning into a
  self-blocking state or authorize unrelated product paths
