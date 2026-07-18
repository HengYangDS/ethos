## MODIFIED Requirements

### Requirement: Provider projections remain generated and behavior-aligned

ETHOS SHALL keep provider-specific CI configuration as generated projections of
tracked templates and SHALL invoke owner scripts rather than duplicating policy
inside provider YAML. GitLab and GitHub projections SHALL be equal CI/CD planes
for remote branches `dev`, `main`, and `submit/*`; the local-only
`candidate/dev` branch SHALL be excluded from both provider projections.

#### Scenario: provider templates and projections remain equal

- **WHEN** CI projection validation runs
- **THEN** each hosted provider projection SHALL byte-match its declared
  template
- **AND** each projection SHALL invoke the same required owner scripts.

#### Scenario: local candidate is excluded from hosted providers

- **WHEN** the GitLab and GitHub CI projections are inspected
- **THEN** each SHALL include `dev`, `main`, and `submit/*` branch selection
- **AND** neither SHALL include `candidate/dev`.
