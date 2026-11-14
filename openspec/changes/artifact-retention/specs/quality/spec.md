## ADDED Requirements

### Requirement: Hosted artifacts expire after one declared retention

A pipeline model SHALL declare its artifact retention once, as 14 days, and its projections SHALL
carry that value on every artifact a hosted job keeps: `retention-days: 14` on each GitHub upload
step and `expire_in: 14 days` on each GitLab `artifacts` block. The common CI model SHALL carry the
same retention on every verification job it generates.

#### Scenario: A hosted job keeps an artifact

- **WHEN** the pipeline model gives a GitHub job an upload step or a GitLab job an `artifacts`
  block
- **THEN** the generated workflow declares `retention-days: 14` on that step
- **AND** the generated GitLab pipeline declares `expire_in: 14 days` on that block

#### Scenario: A repository compiles the common verification jobs

- **WHEN** a repository compiles its projections from the common CI model
- **THEN** the upload step of its generated GitHub verification job declares `retention-days: 14`
- **AND** each generated GitLab verification job declares `expire_in: 14 days` in its `artifacts`
