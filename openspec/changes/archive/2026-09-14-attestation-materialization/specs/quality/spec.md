## REMOVED Requirements

### Requirement: Hook contract queries preserve bounded observation failures

**Reason**: An immutable package declaration is data, not a reason to start a
second interpreter. Executable query timing must not determine hook readiness.

**Migration**: The single package declaration replaces Python launcher literals
and child queries. Existing packages lacking it require native successor
installation, never in-place modification or reinstating the query transport.
Read failures still unarm admission and failed activation still rolls back.

## ADDED Requirements

### Requirement: Hook declarations are selected immutable package data

The selected immutable package SHALL own one validated hook declaration.
Inspection SHALL read that manifest-bound declaration without a child process
or caller-source substitution. Missing data SHALL request successor installation;
unreadable or invalid data SHALL leave admission unarmed. Activation SHALL
preserve existing rollback and exact failure diagnostics.

#### Scenario: A predeclaration package is selected

- **WHEN** a selected package has no declarative hook contract
- **THEN** the reader reports missing support and derives the successor installation command
- **AND** it neither reinstalls the old package nor starts its historical query

#### Scenario: A package declaration is inspected

- **WHEN** native launchers are inspected from a selected package
- **THEN** the one declaration owner renders exact bytes without importing package policy
- **AND** no child process is started merely to read constants

#### Scenario: A declaration read fails during activation

- **WHEN** selected declaration data cannot be read after activation begins
- **THEN** the existing transaction restores prior selector, configuration and state
- **AND** public output retains the declaration failure instead of reporting armed hooks
- **AND** no implicit observation retry or effect replay occurs

#### Scenario: Selected declaration bytes drift

- **WHEN** selected declaration bytes differ from their runtime inventory
- **THEN** runtime currentness fails before the changed declaration can arm hooks
- **AND** neither cached values nor the invoking package declaration substitute
