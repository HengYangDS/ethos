## ADDED Requirements

### Requirement: Control replacement preserves trusted prior verification

Control-replacement admission SHALL read its verification floor from the exact
accepted predecessor. A proposed policy may strengthen but cannot weaken that
floor during its own acceptance. Execution adapters, runtime selection, hook
admission and Git-effect code SHALL belong to the control boundary.

#### Scenario: Candidate cannot disable its required verifier

- **WHEN** a candidate replaces a required accepted verification policy with disabled
- **THEN** control replacement still requires evidence under the prior policy

#### Scenario: Executing authority is not an ordinary unverified change

- **WHEN** runtime selection, hook execution or Git-effect implementation changes
- **THEN** admission classifies the changed path as control and applies that policy
