## ADDED Requirements

### Requirement: Publication peer names default from their declaration

The peer ID and Git remote name SHALL be independently configurable. Within an explicit peer
declaration only, an omitted ID SHALL default to the declared provider and an omitted Git remote
SHALL default to the resolved ID. Defaults SHALL NOT create undeclared peers, infer a provider or
rename existing remotes. Explicit empty or invalid names and duplicate resolved identities SHALL
fail closed before observation or mutation.

#### Scenario: Selected providers use conventional configurable defaults

- **WHEN** GitLab or GitHub is explicitly declared without an ID or Git remote name
- **THEN** the resolved names SHALL be `gitlab` or `github` respectively
- **AND** an explicit ID or remote SHALL replace only its corresponding default
- **AND** no `origin` remote or undeclared provider SHALL be introduced

#### Scenario: Several independently named instances share one provider

- **WHEN** peers `gitlab_a`, `gitlab_b` and `github` are explicitly declared
- **THEN** both GitLab peers SHALL use the GitLab adapter without sharing identity
- **AND** publication SHALL support selecting any declared subset independently
