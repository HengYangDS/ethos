## ADDED Requirements

### Requirement: Skills V2 Conformance Fixtures

ETHOS SHALL keep Skills V2 conformance, migration replay, and parity fixtures
outside runtime semantic packages.

#### Scenario: placeholder skill is rejected

- **WHEN** Skills V2 conformance tests run against a minimal placeholder
  `SKILL.md`
- **THEN** the fixture reports required quality gaps

#### Scenario: adopter migration replay remains compatible

- **WHEN** Skills V2 migration replay tests run against ETHOS v1, dmgr v1, and
  di-effect style activation records
- **THEN** each input normalizes into the provider-neutral IR without losing
  legacy fields
