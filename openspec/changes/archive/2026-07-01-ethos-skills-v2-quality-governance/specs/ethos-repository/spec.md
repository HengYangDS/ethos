## MODIFIED Requirements

### Requirement: Changed Scope Playbook Routing

ETHOS SHALL route changed-scope playbook requests through explicit playbook
metadata and changed-path evidence rather than subject or identifier substring
matches.

#### Scenario: Changed scope route is explicit

- **WHEN** `ethos playbooks route --changed --mode v2-strict --json` runs
- **THEN** every selected playbook has matched changed paths, V2 routing
  evidence, operation metadata, and runnable closure obligations
- **AND** unmatched changed paths are reported as required gaps

#### Scenario: presence-only playbooks do not close report scoring

- **GIVEN** a repository only has a placeholder playbook projection
- **WHEN** `ethos report --json` runs
- **THEN** ETHOS does not give the playbook capability full score from file
  presence alone

### Requirement: Adoption Scaffold

ETHOS SHALL generate repository governance surfaces for `.ethos`, official
OpenSpec records, repo-local skills, docs, claims, evidence placeholders, and
hosted CI projections.

#### Scenario: A repository is adopted

- **WHEN** `ethos adopt --profile gitlab --apply` runs on an empty repository
- **THEN** the planned and written files include V2 skill activation metadata,
  official-quality skill package content, and package manifest records
