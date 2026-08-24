## ADDED Requirements

### Requirement: Selected package runtime is the executable authority

A governed repository SHALL select exactly one validated immutable package runtime under its Git common directory. Package-only commands and generated Git hooks SHALL execute that selected runtime without consulting ambient `PATH`, a source checkout, or another mutable runtime registry.

#### Scenario: package command is absent from PATH
- **WHEN** a governed repository has a valid selected package runtime and `ethos` is absent from `PATH`
- **THEN** its generated hook and public remediation command execute the selected runtime by absolute path
- **AND** both identify the same runtime digest and source identity.

#### Scenario: selector is missing or malformed
- **WHEN** the runtime selector is absent, unreadable, non-canonical, or identifies a runtime whose manifest or files do not validate
- **THEN** package execution and governed mutation fail before invoking another runtime
- **AND** no ambient executable or historical launcher binding is used as fallback.
