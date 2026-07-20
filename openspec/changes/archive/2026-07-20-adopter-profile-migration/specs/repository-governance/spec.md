## ADDED Requirements

### Requirement: Adopter profile is a strict, migratable repository binding
ETHOS SHALL validate an adopter profile through one typed repository binding
contract. It SHALL accept only the current declared fields, except for the
explicitly enumerated historical declaration fields needed to normalize a
former profile. The normalization SHALL be deterministic, SHALL discard only
retired metadata, and SHALL reject unknown, malformed, or semantically
incompatible data.

#### Scenario: Former profile normalizes to the current contract
- **WHEN** an adopter profile contains the historical version metadata and
  repository metadata with their declared historical values
- **THEN** ETHOS SHALL load the profile as valid current contract data
- **AND** it SHALL preserve current typed roots, proof gates, and OpenSpec
  material paths.

#### Scenario: Unsupported legacy data remains blocked
- **WHEN** an adopter profile contains an unknown field, an invalid path, or a
  malformed retired field
- **THEN** ETHOS SHALL report
  `adopter_profile_invalid:.ethos/profile.toml`
- **AND** it SHALL not silently ignore or reinterpret the data.

### Requirement: Normative files remain distinct from directory roots
ETHOS SHALL allow an adopter profile to declare one or more repository-relative
normative source files independently from its directory roots. It SHALL retain
the existing path safety rules for roots and SHALL not treat a declared file as
a directory.

#### Scenario: Root-level normative source is declared
- **WHEN** an adopter declares `normative_sources = ["guidelines.md"]`
- **THEN** ETHOS SHALL include `guidelines.md` in profile evidence-root
  candidates
- **AND** it SHALL keep `roots.rules` as an ordinary safe repository path.

### Requirement: Invalid adopter profile commands return structured blocks
Every public ETHOS reader, planning, proof, landing, report, and OpenSpec
lifecycle command SHALL return a structured `EthosResult` when the target
adopter profile is invalid. The result SHALL contain the stable invalid-profile
gap and SHALL not emit an uncaught traceback as its command result.

#### Scenario: JSON reader observes an invalid profile
- **WHEN** `ethos orient --json` or `ethos report --json` targets an invalid
  adopter profile
- **THEN** it SHALL emit parseable JSON with `ok = false`
- **AND** `required_gaps` SHALL contain
  `adopter_profile_invalid:.ethos/profile.toml`.

#### Scenario: Enforcing proof command observes an invalid profile
- **WHEN** `ethos prove --json` targets an invalid adopter profile
- **THEN** it SHALL emit parseable blocked JSON and exit non-zero
- **AND** it SHALL not start a mutation or create proof evidence.

#### Scenario: Landing does not mask an invalid adopter profile
- **WHEN** `ethos land --json` targets an invalid adopter profile
- **THEN** it SHALL emit parseable JSON with the invalid-profile gap before
  reporting another mutation-admission gap
- **AND** `ethos land --apply --json` SHALL exit non-zero after emitting that
  same structured result.
