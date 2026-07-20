## MODIFIED Requirements

### Requirement: Adopter profile is a strict, migratable repository binding
ETHOS SHALL validate an adopter profile through one typed repository binding
contract. It SHALL accept only the current declared fields, except for the
explicitly enumerated historical declaration fields needed to normalize a
former profile. The normalization SHALL be deterministic, SHALL discard only
retired metadata, SHALL translate the documented former
`roots.rules = "."` workaround only with that complete historical envelope,
and SHALL reject unknown, malformed, or semantically incompatible data.

#### Scenario: Former profile normalizes to the current contract
- **WHEN** an adopter profile contains the historical version metadata and
  repository metadata with their declared historical values, including the
  former `roots.rules = "."` workaround for one root-level normative file
- **THEN** ETHOS SHALL load the profile as valid current contract data
- **AND** it SHALL preserve current typed roots, proof gates, and OpenSpec
  material paths
- **AND THEN** it SHALL derive `normative_sources = ["guidelines.md"]` only
  when that former declaration did not already declare normative sources.

#### Scenario: Unsupported legacy data remains blocked
- **WHEN** an adopter profile contains an unknown field, an invalid path, a
  malformed retired field, or a current-profile use of `roots.rules = "."`
- **THEN** ETHOS SHALL report
  `adopter_profile_invalid:.ethos/profile.toml`
- **AND** it SHALL not silently ignore or reinterpret the data.
