## ADDED Requirements

### Requirement: Provider-neutral Self Audit
ETHOS repository lifecycle semantics SHALL accept provider reports through
explicit composition rather than importing provider execution packages.

#### Scenario: Deep self-audit is requested inside repository semantics
- **WHEN** repository self-audit runs in deep mode without an injected provider
- **THEN** it reports `openspec_reporter_not_configured`
- **AND** it does not import or execute provider-specific OpenSpec adapters

#### Scenario: Deep self-audit is composed by the command plane
- **WHEN** `ethos self audit --mode deep --json` runs in the product repository
- **THEN** the CLI composes repository self-audit with the official OpenSpec
  adapter and reports no provider-configuration gap
