## ADDED Requirements

### Requirement: Record roots extend redaction, not immutability

A repository profile MAY declare `record_roots`, safe repository-relative directories. The effective
record roots SHALL be the paradigm's immutable roots plus `record_roots`, and declaring a root SHALL
add no immutability. A file path SHALL make the profile invalid.

#### Scenario: Record directories are declared

- **WHEN** a profile declares `record_roots = ["docs/decisions/"]`
- **THEN** the effective record roots are `openspec/changes/archive/` and `docs/decisions/`
- **AND** an ordinary lane may still edit `docs/decisions/`

#### Scenario: A file is declared as a record root

- **WHEN** a profile declares `record_roots = ["CHANGELOG.md"]`
- **THEN** ETHOS reports `repository_profile_invalid:.ethos/profile.toml`
