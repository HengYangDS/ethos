## MODIFIED Requirements

### Requirement: Singular Gate Declaration

`system/gates.toml` SHALL be the only product gate and proof-floor declaration.
A gate SHALL bind either one or more concrete Python providers or one external
owner command, never both. Every gate SHALL belong to this one graph without a
secondary registry selector, and no tool catalog SHALL restate gate identity,
profile membership, or execution ownership.

#### Scenario: A gate is loaded

- **WHEN** ETHOS validates or compiles the gate declaration
- **THEN** strict Pydantic contracts reject unknown fields, duplicate IDs,
  duplicate executors, missing dependencies, and unknown proof-set members
- **AND** provider references and external commands remain adapter identities,
  not public CLI commands
- **AND** no second Python registry, registry projection, or tool catalog
  restates the declaration

#### Scenario: A Python provider gate executes

- **WHEN** `ethos prove --execute --gate <gate-id> --json` selects a provider gate
- **THEN** the provider is invoked directly in the admitted checkout
- **AND** every provider returns a mapping with an explicit `verdict` result and
  required gaps
- **AND** the proof run records the gate, provider identity, diagnostics, and
  closed verdict
- **AND** ETHOS does not call its CLI through a subprocess or in-process loopback

### Requirement: One Owner Per Property

Ruff, the selected type checker, pytest/coverage, rumdl or markdownlint, dprint or
native carrier formatters, shfmt/ShellCheck, ast-grep, import-linter, dependency
checking, and repository-native semantic checks SHALL each own a disjoint
property. Gate identity and proof membership SHALL remain in
`system/gates.toml`; tool-specific behavior and version identity SHALL remain in
the smallest existing native configuration or supply owner.

#### Scenario: Two tools claim the same property

- **WHEN** gate, native configuration, supply, and owner-script declarations are
  audited
- **THEN** the overlap is a required gap unless one tool is explicitly a bounded
  pilot replacing the other
- **AND** a catalog, baseline, hosted dashboard, or convenience wrapper cannot
  become a second authority

### Requirement: Repository semantic ownership is closed

ETHOS SHALL mechanically derive a finite semantic relation from current native
repository carriers and SHALL require every governed semantic identity to have
exactly one current owner and a complete producer, consumer, and selector
relation. The evaluation SHALL preserve provenance until it has classified all
missing, duplicate, orphan, superseded, conflicting, and unknown relations.

#### Scenario: A semantic identity has two current owners

- **WHEN** two current native declarations claim the same governed identity
- **THEN** repository audit reports a duplicate-owner gap naming both sources
- **AND** set deduplication does not hide the conflict

#### Scenario: A required relation is incomplete

- **WHEN** a current producer, consumer, or selector lacks its required
  counterpart
- **THEN** repository audit reports the precise orphan or missing relation
- **AND** the aggregate verdict is not `pass`

#### Scenario: Native carriers supply executable ownership

- **WHEN** repository audit derives executable owners
- **THEN** host executables come from the runtime surface, downloaded tools from
  native supply policy, and script executables only from scripts selected by a
  gate or provider plus their explicit transitive script calls
- **AND** an unselected script or unrelated configuration file does not become
  an owner merely because it exists

#### Scenario: Historical material mentions a retired identity

- **WHEN** an archived Change, evidence record, generated artifact, example, or
  superseded document contains an old identity
- **THEN** it is not admitted as a current owner or consumer
- **AND** exclusion follows structural carrier state rather than a literal
  exception list

#### Scenario: A current specification prohibits a retired command

- **WHEN** an OpenSpec scenario names a retired command only as the object of a
  prohibition or rejection rule
- **THEN** repository audit does not classify that command as a current consumer
- **AND** positive GIVEN or WHEN command subjects remain observable consumers

#### Scenario: A selected carrier cannot be parsed

- **WHEN** a current selected Markdown, TOML, JSON, YAML, or Python carrier
  cannot be parsed by its native parser
- **THEN** repository audit reports that exact carrier as `unknown`
- **AND** the parse failure cannot collapse into an empty passing observation
