## ADDED Requirements

### Requirement: Locale-Stable External CLI Assertions

ETHOS local quality tests SHALL bind human-readable external CLI assertions to
a deterministic message locale when the asserted semantics are represented
only by localized text.

#### Scenario: Git bundle complete-history verification

- **GIVEN** a cross-host handoff bundle created by the ETHOS test fixture
- **WHEN** the test invokes `git bundle verify`
- **THEN** the command SHALL execute successfully
- **AND** the complete-history text assertion SHALL use the C message locale
- **AND** the surrounding test process and shared Git helpers SHALL remain
  unchanged.
