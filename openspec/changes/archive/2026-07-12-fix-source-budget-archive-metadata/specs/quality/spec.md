## MODIFIED Requirements

### Requirement: Global Executable Source Budget And Compression Debt

ETHOS SHALL measure maintained executable source across product code, tests,
tools, shell, JavaScript, declarations, schemas, templates, and tracked derived
projections, and SHALL reject an unbounded source increase that lacks an explicit
compression-debt record. Archived OpenSpec `.openspec.yaml` headers SHALL remain
historical closeout metadata rather than executable source.

#### Scenario: Archived OpenSpec metadata remains historical evidence

- **WHEN** `ethos quality source-budget --json` evaluates archived OpenSpec
  change records
- **THEN** it SHALL exclude only the `.openspec.yaml` metadata file beneath
  `openspec/changes/archive/`
- **AND** active OpenSpec metadata and every other tracked YAML carrier SHALL
  remain in the source-budget inventory
- **AND** the exclusion SHALL not broaden to archived proposals, designs, tasks,
  specification deltas, or arbitrary YAML paths.
