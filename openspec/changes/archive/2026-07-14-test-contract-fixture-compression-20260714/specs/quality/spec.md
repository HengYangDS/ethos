## ADDED Requirements

### Requirement: Declarative CLI Lifecycle Fixture Reuse

ETHOS SHALL reuse test-only literal fixture builders for repeated CLI lifecycle
topology and Git commit mechanics when formatter-clean scoped test ELOC is a
net deletion and every command-specific public assertion remains in its named
test.

#### Scenario: Work-Lane lifecycle contracts retain their command boundary

- **WHEN** land or publish tests require an adopted accepted root, candidate
  worktree, owned Work Lane, or a committed fixture file
- **THEN** a typed test-only helper MAY construct that topology or commit
  literal file content
- **AND THEN** each named test SHALL invoke its own command and assert its own
  state, gaps, and payload contract.

### Requirement: Canonical Workspace-Status Schema Sample Reuse

ETHOS SHALL reuse the canonical valid workspace-status schema sample for
schema acceptance and focused forbidden-field rejection tests when the sample
contains the complete required envelope.

#### Scenario: UI projection fields remain rejected

- **WHEN** a workspace-status schema test adds a forbidden UI projection field
  to the canonical valid sample
- **THEN** validation SHALL fail with required gaps
- **AND THEN** the test SHALL not maintain a second full workspace-status
  fixture.
