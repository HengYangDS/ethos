## ADDED Requirements

### Requirement: Declared file-size policy is strict and observable

ETHOS SHALL compile an optional file-size policy through the rules configuration
owner. Declared ceilings SHALL be positive integer multiples of one hundred,
without coercion, unknown fields or per-file exemptions. Omitted role limits
SHALL inherit the declared default. An absent declaration SHALL impose no hidden
generic ceiling; malformed declarations SHALL block rather than become absent.

#### Scenario: Invalid or coercible policy

- **WHEN** a present declaration has invalid TOML, shape, field names or limits
- **THEN** the public size gate blocks with a policy-path-bound cause
- **AND** booleans, strings, floats, zero and fractional hundreds are not limits
- **AND** continuation derives exact prewrite without granting write authority

#### Scenario: Optional policy is absent

- **WHEN** a generic repository has no file-size declaration
- **THEN** the report states not configured without imposing a runtime ceiling
- **AND** this does not authorize removing repository-required governance policy

#### Scenario: Valid ceiling is enforced

- **WHEN** a measured file equals its declared role ceiling
- **THEN** that boundary passes and one additional effective line blocks
- **AND** unused capacity elsewhere cannot compensate for the violation

#### Scenario: Invalid and unavailable source differ

- **WHEN** a source has invalid Python syntax or encoding
- **THEN** the report blocks with the path and cause rather than a fallback count
- **AND** an inaccessible required source or policy remains unknown
- **AND** neither failure is reported as measured zero or a valid absent input
