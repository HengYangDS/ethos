## ADDED Requirements

### Requirement: Gate providers resolve by catalog ID

A gate declaration SHALL name each provider by a catalog ID of the form `provider.<name>`. One
packaged data table, and no alias module, SHALL map each ID to its implementation and each legacy
`ethos.<module>:<callable>` name to its ID. A legacy name SHALL keep resolving for one support
window, at least two weekly release batches after the catalog's first release; only a named Breaking
change SHALL remove it. A name the catalog does not resolve SHALL refuse the proof before any gate
runs.

#### Scenario: A declaration names a catalog ID

- **WHEN** a selected gate declares `provider.docs-registry`
- **THEN** the docs-registry provider runs
- **AND** the gate's result records that provider under the declared ID

#### Scenario: A declaration still names a legacy name

- **WHEN** a selected gate declares an `ethos.<module>:<callable>` name that the table maps
- **THEN** the gate runs the provider of the mapped ID and gives the report and verdict that the ID
  gives
- **AND** the gate's result carries the note `gate_provider_legacy_name`, which names the ID to
  declare
- **AND** the gate's execution identity and its recorded provider name stay the declared name

#### Scenario: A repository redeclares a shared gate by a legacy name

- **WHEN** a repository's registry declares a shared gate by a legacy name and the packaged registry
  declares the same provider by its ID
- **THEN** the two declarations compose without `common_gate_execution_conflict`
- **AND** the packaged declaration governs the gate

#### Scenario: A name does not resolve

- **WHEN** a selected gate declares an ID that the catalog lacks, or a legacy name that the table
  does not map
- **THEN** the proof refuses with `gate_provider_unresolved:<gate>:<name>`
- **AND** no gate runs

#### Scenario: The table is checked

- **WHEN** the catalog table is validated
- **THEN** each ID has its own importable callable
- **AND** each legacy name maps to one ID
