## ADDED Requirements

### Requirement: accepted proof without active Change

A clean accepted root with no active OpenSpec Change SHALL execute package-only
governance and full proof without requiring a synthetic Change status payload.
Active or completed Changes SHALL retain strict status and artifact validation.

#### Scenario: all Changes are archived

- **WHEN** the official OpenSpec list is empty on a clean accepted root
- **THEN** governance uses an empty optional status payload and full proof proceeds

#### Scenario: a Change is active

- **WHEN** the official OpenSpec list selects an active Change
- **THEN** missing or invalid status and artifact fields remain blocking gaps
