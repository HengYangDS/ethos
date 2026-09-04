## ADDED Requirements

### Requirement: Full proof validates deterministic hosted projections

ETHOS SHALL include each deterministic repository-owned syntax validator used
by hosted acceptance in its canonical full proof set. The gate SHALL invoke the
existing validator owner directly, bind its exact command and policy identity
into proof evidence, and retain hosted provider execution as a separate evidence
plane.

#### Scenario: A GitHub workflow uses an invalid expression context

- **WHEN** a tracked GitHub Actions projection contains an expression or context
  that the provider rejects deterministically
- **THEN** exact-HEAD full proof fails through the declared GitHub workflow
  syntax gate before publication
- **AND** the gate invokes the repository's existing actionlint owner exactly
  once
- **AND** a local syntax result does not claim that hosted GitHub CI passed.

#### Scenario: A hosted workflow projection is valid

- **WHEN** the tracked template and generated GitHub workflow are equal and the
  declared syntax owner accepts the generated workflow
- **THEN** exact-HEAD full proof records the syntax gate's command identity and
  passing result
- **AND** hosted GitHub CI remains independently observable after publication.
