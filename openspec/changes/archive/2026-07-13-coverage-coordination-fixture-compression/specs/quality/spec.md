## ADDED Requirements

### Requirement: Declarative Cross-Host Handoff Test Command Envelopes

ETHOS SHALL factor a finite family of equivalent cross-host handoff test command
envelopes into one bounded typed local helper when the formatter-clean scoped
representation is a net deletion and each case-specific input and result remains
explicit.

#### Scenario: Export modes retain independent behavior

- **WHEN** a cross-host export uses a file or text context and clean, omitted,
  committed, or preserved dirty disposition
- **THEN** each test SHALL retain its distinct expected success or blocking
  result through the shared command envelope.
