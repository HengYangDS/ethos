## ADDED Requirements

### Requirement: Progressive disclosure for agent context
ETHOS SHALL structure agent-facing documentation so agents can load a thin
entrypoint first and expand only into task-relevant rules, skills, design docs,
references, and evidence.

#### Scenario: Agent loads minimal context first
- **WHEN** an agent starts work in a governed repository
- **THEN** the first loaded surface is a thin entrypoint that links to canonical
  rule, skill, design, OpenSpec, and evidence surfaces
- **AND** detailed operating semantics remain in task-specific files rather than
  the entrypoint

#### Scenario: Agent expands by task need
- **WHEN** the changed scope matches a task-specific rule or skill route
- **THEN** the agent loads that specific rule or skill and its direct references
- **AND** avoids bulk-loading unrelated docs, generated artifacts, or host
  projections

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
