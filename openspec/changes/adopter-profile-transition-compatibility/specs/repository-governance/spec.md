## ADDED Requirements

### Requirement: Deployed adopter readers remain bounded

ETHOS SHALL inspect the exact deployed transition and terminal-v1 repository
carrier without making either a proof or mutation authority.

#### Scenario: Package-only readers execute

- **WHEN** an installed wheel reads the deployed adopter fixture
- **THEN** `status` and `plan` SHALL pass without traceback
- **AND** `plan` SHALL bind carrier bytes, deny authority, and emit no v2 plan
- **AND** any transition-row drift SHALL fail closed.
