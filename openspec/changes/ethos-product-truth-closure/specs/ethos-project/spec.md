## ADDED Requirements

### Requirement: Diagnosable Adoption Scaffold
ETHOS SHALL generate a scaffold that is immediately diagnosable through the
public command plane.

#### Scenario: Scaffold is applied to a non-Git directory
- **WHEN** `ethos init --apply --root <dir>` is run
- **THEN** ETHOS writes repository governance files, OpenSpec records,
  repo-local skills, docs, claims, evidence placeholders, and ignored local
  state configuration
- **AND** `ethos status --root <dir> --json` returns schema-valid JSON instead
  of crashing
- **AND** missing Git initialization is reported as `git_repository_missing`

#### Scenario: Apply mode is explicit
- **WHEN** `ethos init --apply` or `ethos adopt --apply` is invoked
- **THEN** ETHOS applies the scaffold without requiring an additional dry-run
  negation flag
