## REMOVED Requirements

### Requirement: Skills V2 Conformance Fixtures

**Reason**: Implicit historical-field migration conflicts with the current
activation schema; a development-generation name is not a separate capability.

**Migration**: Skill Conformance Fixtures preserves supported conformance and
requires explicit rejection of unsupported inputs without rewriting raw evidence.

## ADDED Requirements

### Requirement: Skill Conformance Fixtures

ETHOS SHALL keep skill conformance and parity fixtures outside runtime semantic
packages. Supported input SHALL preserve its declared meaning; unsupported input
SHALL fail explicitly instead of retaining obsolete compatibility behavior.

#### Scenario: placeholder skill is rejected

- **WHEN** conformance checks evaluate a minimal placeholder skill
- **THEN** required package-quality gaps remain observable

#### Scenario: Unsupported activation is not normalized into success

- **WHEN** a fixture supplies an unsupported activation version or retired fields
- **THEN** current validation rejects the original input
- **AND** raw fixture evidence is not rewritten or promoted to current authority
