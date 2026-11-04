## ADDED Requirements

### Requirement: Hosted host conformance retains its stage timings

Each hosted host conformance job SHALL upload the execution events of its package acceptance with
its receipt, including after a failure. The events record stage timing only.

#### Scenario: A host conformance leg ends

- **WHEN** a GitHub or GitLab host conformance job ends, passing or failing, after its package
  acceptance started
- **THEN** its artifact contains `build/evidence/local-install/smoke.events.jsonl`
- **AND** it contains `build/evidence/local-install/smoke.json` when the acceptance wrote one.
