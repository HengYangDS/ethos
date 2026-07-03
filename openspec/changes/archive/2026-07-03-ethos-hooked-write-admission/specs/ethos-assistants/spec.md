## MODIFIED Requirements

### Requirement: Playbook Projection

ETHOS SHALL discover repo-local skills from ETHOS activation registry inputs,
normalize them into a provider-neutral skill activation IR, and keep
provider-visible skill packages as digest-bound projections over repository
truth rather than truth stores.

#### Scenario: Campaign manifests route to governance playbooks

- **WHEN** changed-scope routing sees `evolution/campaigns/**` or source
  `skills/**` activation paths
- **THEN** ETHOS selects the repository-governance playbook
- **AND** reports no unmatched changed-scope path for those governance
  surfaces.
