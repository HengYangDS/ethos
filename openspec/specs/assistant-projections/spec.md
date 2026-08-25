# ETHOS Assistant Projections

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

- **WHEN** `ethos prove --gate playbooks-v2 --json` runs
- **THEN** ETHOS reports normalized V2 registry metadata, package quality,
  package digest state, routing coverage, projection drift, portfolio coverage,
  portfolio design diagnostics, and required or advisory gaps

#### Scenario: strict mode rejects placeholder skills

- **GIVEN** a repo-local skill contains only a thin placeholder
- **WHEN** `ethos prove --gate playbooks-v2 --json` runs
- **THEN** ETHOS reports a required gap for official skill package quality

#### Scenario: strict mode rejects overlapping skill route owners

- **GIVEN** active repo-local skills declare the same exact changed-path route
  glob in activation metadata
- **WHEN** `ethos prove --gate playbooks-v2 --json` runs
- **THEN** ETHOS reports a deterministic `skill_portfolio_path_glob_duplicate`
  required gap
- **AND** the payload exposes `portfolio_design` diagnostics without making
  skills a repository truth center

#### Scenario: strict mode rejects weak skill entrypoint shape

- **GIVEN** a provider-visible skill entrypoint has a non-trigger description or
  hides long procedure in `SKILL.md` without `references/` or `scripts/`
- **WHEN** `ethos prove --gate playbooks-v2 --json` runs
- **THEN** ETHOS reports a deterministic skill quality required gap

#### Scenario: historical migration fixtures preserve adopter routing evidence

- **GIVEN** a migration fixture contains v1 activation metadata
- **WHEN** Skills V2 migration replay runs
- **THEN** ETHOS preserves readable routing evidence while reporting V2
  migration gaps

#### Scenario: strict mode enforces portfolio coverage

- **GIVEN** activation metadata declares required primary subjects and
  single-owner subjects
- **WHEN** `ethos prove --gate playbooks-v2 --json` runs
- **THEN** ETHOS reports deterministic required gaps for missing active primary
  owners and duplicate active primary owners
- **AND** the check payload exposes the portfolio coverage contract and owner
  map without treating skills as repository truth above source, tests, schemas,
  docs, OpenSpec, claims, evidence, or command JSON

#### Scenario: Skill eval metadata is inspected
- **WHEN** a skill package declares eval metadata
- **THEN** ETHOS validates the metric names, pass@k bounds, instability-gap bounds, treatment id, and evidence refs
- **AND** the metadata is reported as package quality metadata
- **AND** eval metadata does not replace package digests, proof commands, claims, or evidence

### Requirement: Projection Boundary

ETHOS SHALL keep assistant, MCP, ACP, hosted CI, workflow runtimes, external
agent hosts, and provider-visible skill packages as adapters, method packs,
context providers, or projections over repository truth.

#### Scenario: projection drift is audited

- **WHEN** `ethos prove --gate playbooks-v2 --json` runs
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

### Requirement: Exact-tree terminal projection input

ETHOS SHALL export its terminal architecture projection input from one exact Git
commit and tree without reading mutable working-tree content.

#### Scenario: deterministic export ignores working-tree drift

- **GIVEN** one selected commit whose declaration, projection documents, and
  semantic sources exist in that tree
- **WHEN** the terminal projection exporter runs twice for that commit while a
  selected working-tree source differs
- **THEN** both outputs SHALL be byte-identical
- **AND** the output SHALL bind the exact commit, tree, repository-relative
  source paths, source digests, projection-document digests, and one content
  digest
- **AND** no host absolute path or wall-clock timestamp SHALL enter the output.

### Requirement: Projection authority remains bounded

ETHOS SHALL treat the terminal projection declaration as a lossless selection
and export boundary, not as product or effect authority.

#### Scenario: unsafe or incomplete declarations fail closed

- **WHEN** a declaration claims repository-effect authority, a selected source
  is missing or stale, provenance names an unknown source, a relation endpoint
  is unknown, or a semantic item has zero or multiple projection dispositions
- **THEN** export SHALL fail before producing a ProjectionInput
- **AND** no renderer, projection consumer, or generated artifact SHALL mint
  authority or write back into ETHOS.
