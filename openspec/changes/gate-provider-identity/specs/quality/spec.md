## ADDED Requirements

### Requirement: A gate names each provider once

A gate declaration SHALL name a provider at most once among its providers and at most once among
its verification providers. A catalog ID and a legacy name that the catalog maps to that ID name
one provider. A declaration that repeats a provider SHALL be refused where it is validated, before
any gate runs. The gate schema SHALL hold a verification provider reference to the form and the
textual uniqueness to which it holds a provider reference.

#### Scenario: A gate names a provider by its ID and by its legacy name

- **WHEN** a gate declares a catalog ID together with the legacy name that the catalog maps to it,
  among its providers or among its verification providers
- **THEN** the declaration is refused as an invalid gate executor
- **AND** no provider runs

#### Scenario: A gate names two providers under different spellings

- **WHEN** a gate declares one provider by its ID and another by a legacy name, or two names that
  the catalog lacks
- **THEN** the gate contract accepts the declaration
- **AND** a name that the catalog lacks still refuses the proof as unresolved

#### Scenario: A verification provider reference is malformed or repeated

- **WHEN** a gate payload names a verification provider by a bare word, which begins with neither
  `provider.` nor `ethos.`, or names one reference twice
- **THEN** the gate schema refuses the payload
- **AND** the gate contract refuses the same payload
