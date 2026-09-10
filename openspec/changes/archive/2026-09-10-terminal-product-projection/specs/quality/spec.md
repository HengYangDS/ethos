## ADDED Requirements

### Requirement: Terminal projection export preserves complete source meaning

The terminal exporter SHALL bind one exact commit and tree, retain semantic
attributes and graph contracts, and reject stale source bindings. The product
contract remains the sole product meaning owner. The target design SHALL be
identified as a target rather than an implementation claim.

#### Scenario: Whole-product meaning survives export

- **WHEN** the current terminal architecture is exported
- **THEN** interpretation, formation and adoption, capability contracts,
  collaboration outcomes, bounded verification and integration, actual-use
  feedback, recovery and exit remain represented with source provenance
- **AND** Commitment remains transient and accepted intent remains OpenSpec-owned

#### Scenario: Native source drift is not hidden by fixtures

- **WHEN** any selected source changes without semantic reconciliation
- **THEN** the actual-source export regression rejects the digest mismatch
- **AND** isolated synthetic fixture success cannot substitute for that result

### Requirement: Required visual assertions have readable static witnesses

Every required node and relation SHALL select a main-static copy witness or a
meaning-preserving aggregate. Export SHALL reject missing and hidden-only
witnesses. Renderer acceptance SHALL measure actual painted glyphs, transforms,
strokes and arrowheads; metadata or hover alone SHALL NOT satisfy coverage.

#### Scenario: Hidden witness cannot satisfy required meaning

- **WHEN** a required assertion is omitted or its only witness is hidden
- **THEN** source export rejects the disposition
- **AND** a readable aggregate is allowed without duplicating every kernel node

#### Scenario: Compression never erases product meaning

- **WHEN** an old text-count budget conflicts with complete product meaning
- **THEN** readability and semantic completeness remain hard constraints
- **AND** word or object reduction is only an optimization among feasible layouts
