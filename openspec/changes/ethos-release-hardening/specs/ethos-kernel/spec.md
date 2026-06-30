## ADDED Requirements

### Requirement: Official OpenSpec Self-Governance
ETHOS SHALL keep `openspec/` as an official self-governance capability for
spec-driven planning and change records while preserving `ethos ...` as the only
public product command plane.

#### Scenario: OpenSpec is present but bounded
- **WHEN** an agent audits ETHOS product surfaces
- **THEN** `openspec/` is present as official governance record storage and is
  not treated as a replacement for ETHOS kernel, command output, schemas,
  tests, or current docs

#### Scenario: OpenSpec official validation is used
- **WHEN** ETHOS audits OpenSpec self-governance
- **THEN** it invokes the official OpenSpec CLI for status and strict validation
  instead of parsing OpenSpec records with ad hoc repository code
