## ADDED Requirements

### Requirement: Forge provider projections preserve ETHOS repository truth

ETHOS SHALL support GitHub and GitLab as hosted forge providers that project the
same repository governance contract without changing `status -> plan -> prove ->
land -> publish` semantics.

#### Scenario: Dual provider templates mirror one gate contract

- **WHEN** a repository enables both GitHub and GitLab provider profiles
- **THEN** provider templates SHALL invoke repository-owned gate scripts or
  `ethos ...` commands for the same required gate classes
- **AND** provider YAML drift SHALL be checkable from tracked template sources
- **AND** provider-specific syntax checks SHALL NOT be treated as repository
  proof by themselves.

#### Scenario: Local provider emulation remains local evidence

- **WHEN** a GitHub or GitLab provider projection is emulated locally
- **THEN** the evidence SHALL name the local emulator evidence class
- **AND** it SHALL record the provider, template or projection path, command,
  scope, Git head, dirty state, and return code
- **AND** it SHALL explicitly state that hosted provider status was not claimed.

### Requirement: Tool adoption remains profile and adapter scoped

ETHOS SHALL admit mature tooling through contracts, profiles, adapters,
projections, and gates instead of making adopter tools product ontology.

#### Scenario: Planned tools do not become active gates by catalog presence

- **WHEN** a tool is listed in `system/tools.toml` with `planned = true`
- **THEN** ETHOS SHALL NOT report it as an active quality floor
- **AND** activation SHALL require a config owner, reusable execution surface,
  CI or hook projection, and proof coverage.

#### Scenario: Optional method packs remain replaceable

- **WHEN** an agent uses Superpowers or another method pack to plan or review a
  change
- **THEN** the method pack MAY be recorded as execution context
- **AND** repository truth SHALL still require promoted source, docs, OpenSpec,
  claim, evidence, or command proof
- **AND** missing method-pack availability SHALL NOT block ETHOS repository
  governance when equivalent evidence discipline is satisfied.

### Requirement: OpenSpec customization stays official-compatible

ETHOS SHALL apply official OpenSpec validation before ETHOS-specific schema,
capability profile, claim binding, evidence, and archive lifecycle checks.

#### Scenario: ETHOS validates capability metadata after official OpenSpec

- **WHEN** an OpenSpec change or accepted spec is validated for ETHOS governance
- **THEN** official OpenSpec validation SHALL run first
- **AND** ETHOS SHALL validate repo-local capability profiles, proposal facets,
  claim carriers, evidence refs, and archive closeout without replacing official
  OpenSpec syntax or semantics.
