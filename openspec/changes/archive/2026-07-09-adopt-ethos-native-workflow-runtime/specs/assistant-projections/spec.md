## MODIFIED Requirements

### Requirement: Playbook Projection
ETHOS SHALL discover repo-local skills from ETHOS activation registry inputs,
normalize them into a provider-neutral skill activation IR, and keep
provider-visible skill packages as digest-bound projections over repository
truth rather than truth stores.

#### Scenario: Skill eval metadata is inspected
- **WHEN** a skill package declares eval metadata
- **THEN** ETHOS validates the metric names, pass@k bounds, instability-gap bounds, treatment id, and evidence refs
- **AND** the metadata is reported as package quality metadata
- **AND** eval metadata does not replace package digests, proof commands, claims, or evidence
