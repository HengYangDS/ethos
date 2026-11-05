## MODIFIED Requirements

### Requirement: A locked supply refusal names the action that can help

A refusal of incomplete locked supply SHALL name the next action that can complete it. When the selected mise's safe mode drops the dependency graph that a missing tool's lock entry references, as mise 2026.11.0 and 2026.11.1 do, the refusal SHALL name that regression and a mise release that fixes it instead of `mise trust`.

#### Scenario: The selected mise drops the locked graph

- **WHEN** the selected mise is 2026.11.0 or 2026.11.1 and a missing tool's lock entry references a dependency graph
- **THEN** the refusal names that regression and mise 2026.11.2 or later
- **AND** it does not name `mise trust`

#### Scenario: The selected mise has the fix

- **WHEN** the selected mise is 2026.11.2 or later, a missing tool's lock entry references a dependency graph and its root is not trusted
- **THEN** the refusal names `mise trust` as the next action
- **AND** it does not name the regression

#### Scenario: Trust can select the locked install

- **WHEN** a missing tool's root is not trusted and the selected mise can use trust-keyed lock metadata in safe mode
- **THEN** the refusal names `mise trust` as the next action

#### Scenario: The supply is not installed

- **WHEN** a trusted root's declared tool is not installed
- **THEN** the refusal names `mise install --locked` as the next action
