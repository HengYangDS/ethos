## ADDED Requirements

### Requirement: Native dependency audit covers every declared lock ecosystem

The dependency-security owner SHALL audit each declared Python and npm lock with
the selected native tool, preserve per-ecosystem observations, and bind its verdict
to unchanged source, manifests, locks and audit policy. A vulnerability blocks;
missing or invalid evidence is unknown. The same gate SHALL guard package delivery without making offline tests
depend on online advisory availability or claiming hosted assurance.

#### Scenario: npm is vulnerable while Python passes

- **WHEN** the native uv report passes and the native npm report identifies a vulnerable dependency
- **THEN** the aggregate audit blocks and retains both reports
- **AND** dependent package delivery does not run; offline tests remain independently available

#### Scenario: Observation fails or scope is incomplete

- **WHEN** an input is missing or a native audit times out, fails or returns malformed or inconsistent evidence
- **THEN** that ecosystem cannot pass and reports its exact unavailable boundary
- **AND** the other declared ecosystem is still observed within its bound

#### Scenario: Input changes during an audit

- **WHEN** a bound source, manifest, lock or policy changes before the result is recorded
- **THEN** the result is non-passing and cannot be reused as current proof

#### Scenario: Complete native checks pass

- **WHEN** both native audits return valid clean observations over unchanged declared inputs
- **THEN** the aggregate audit passes with exact identities and raw evidence
- **AND** it makes no claim that hosted CI, deployment or user benefit has succeeded
