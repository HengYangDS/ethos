## MODIFIED Requirements

### Requirement: Global Executable Source Budget And Compression Debt

ETHOS SHALL measure maintained executable source across product code, tests,
tools, shell, JavaScript, declarations, schemas, templates, and tracked derived
projections, and SHALL reject an unbounded source increase that lacks an explicit
compression-debt record. When a stale Work Lane is reconstructed on a newer
candidate train, candidate-owned debt records MUST remain visible, every active
record MUST have one registered ISO-8601 deletion wave and expiry, and measured
settlement MUST remove only the named allowance. Reconstruction MUST preserve the
immutable baseline and terminal targets and MUST regenerate evidence from the
successor HEAD.

#### Scenario: A migration reports global source deltas

- **WHEN** `ethos quality source-budget --json` evaluates a governed repository
- **THEN** it reports the baseline identity, current HEAD, global and carrier
  metrics, independent inventory status, terminal budgets, and active debt
- **AND** the metric does not exclude a tracked executable carrier merely because
  its logic moved from Python into TOML, CEL, Jinja, generated output, tests, or
  tools
- **AND** each active debt record names the added surface, owner, replacement,
  expiry, deletion wave, and expected net deletion
- **AND** a stale, missing, expired, or over-budget debt record is a required gap

#### Scenario: Archived OpenSpec metadata remains historical evidence

- **WHEN** `ethos quality source-budget --json` evaluates archived OpenSpec
  change records
- **THEN** it SHALL exclude only the `.openspec.yaml` metadata file beneath
  `openspec/changes/archive/`
- **AND** active OpenSpec metadata and every other tracked YAML carrier SHALL
  remain in the source-budget inventory
- **AND** the exclusion SHALL not broaden to archived proposals, designs, tasks,
  specification deltas, or arbitrary YAML paths.

#### Scenario: Successor reconstruction preserves candidate debt and settled deletion

- **GIVEN** a source-budget Work Lane is stale behind `candidate/dev`
- **AND** candidate has added valid debt records while the stale Lane has measured settlement of a distinct record
- **WHEN** ETHOS reconstructs source-budget behavior in a new candidate-based Work Lane
- **THEN** the resulting policy retains candidate-only records with explicit lifecycle fields
- **AND** it removes only the settled record's allowance
- **AND** its aggregate allowance equals the sum of all retained active records
- **AND** it preserves the declared baseline and terminal limits
- **AND** stale parity, proof, and claim artifacts are regenerated rather than replayed as evidence

#### Scenario: Active debt rollover remains bounded and explicit

- **GIVEN** inherited active debt waves and matching record expiries are dated July 17, 2026
- **AND** the candidate train advances before the successor can produce clean proof
- **WHEN** the successor records its one-time lifecycle rollover
- **THEN** the inherited active waves and matching expiries move to July 18, 2026
- **AND** no record ID, expected deletion, allowance, aggregate cap, baseline, terminal limit, or settled deletion changes
- **AND** a later rollover requires a new recorded decision rather than an implicit extension
