# ETHOS Assistants

## Purpose

ETHOS SHALL expose assistant, MCP, ACP, context, and repo-local skills as thin
projections over repository truth.
## Requirements
### Requirement: Playbook Projection

ETHOS SHALL discover repo-local skills from ETHOS activation registry inputs,
normalize them into a provider-neutral skill activation IR, and keep
provider-visible skill packages as digest-bound projections over repository
truth rather than truth stores.

#### Scenario: Playbooks are checked

- **WHEN** `ethos playbooks check --json` runs
- **THEN** ETHOS reports normalized V2 registry metadata, package quality,
  package digest state, routing coverage, projection drift, and required or
  advisory gaps

#### Scenario: strict mode rejects placeholder skills

- **GIVEN** a repo-local skill contains only a thin placeholder
- **WHEN** `ethos playbooks check --mode v2-strict --json` runs
- **THEN** ETHOS reports a required gap for official skill package quality

#### Scenario: historical migration fixtures preserve adopter routing evidence

- **GIVEN** a migration fixture contains v1 activation metadata
- **WHEN** Skills V2 migration replay runs
- **THEN** ETHOS preserves readable routing evidence while reporting V2
  migration gaps

### Requirement: Projection Boundary

ETHOS SHALL keep assistant, MCP, ACP, hosted CI, workflow runtimes, external
agent hosts, and provider-visible skill packages as adapters, method packs,
context providers, or projections over repository truth.

#### Scenario: projection drift is audited

- **WHEN** `ethos quality projection-drift --json` runs
- **THEN** ETHOS reports package, registry, generator, and projection drift
  records without accepting host metadata as authority

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
