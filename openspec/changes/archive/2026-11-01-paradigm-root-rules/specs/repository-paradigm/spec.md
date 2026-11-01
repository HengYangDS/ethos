## MODIFIED Requirements

### Requirement: Agent and reader entry is singular

Every governed repository SHALL keep `AGENTS.md`, `CONTRIBUTING.md` and `README.md` at its root.
`AGENTS.md` SHALL be the only agent entry; repository-local Skills SHALL live under
`.agents/skills/`.

#### Scenario: A repository lacks the agent entry

- **WHEN** a governed repository has no root `AGENTS.md`
- **THEN** the paradigm reports a missing entry document.

#### Scenario: A repository lacks the contributor guide

- **WHEN** a governed repository that publishes to two forges has no root `CONTRIBUTING.md`
- **THEN** the paradigm reports a missing entry document

### Requirement: Publication peers name their Git remotes after themselves

With two or more publication peers declared in `.ethos/release.toml`, each SHALL name its Git remote
by its own peer id, so a GitLab peer `gitlab` uses the remote `gitlab` and a GitHub peer `github`
uses `github`, and none SHALL use the clone remote name. A sole publication peer MAY keep the clone
remote name, which the repository paradigm declares as Git's default `origin`, the name `git clone`
gives the one remote it clones from.

#### Scenario: A peer keeps the implicit remote name

- **WHEN** the release binding declares the peers `gitlab` and `github`, and `gitlab` has
  `git_remote = "origin"`
- **THEN** the paradigm reports the peer and the rename to `gitlab`.

#### Scenario: A sole peer keeps the clone's name

- **WHEN** the release binding declares only the peer `gitlab`, with `git_remote = "origin"`
- **THEN** the paradigm reports no remote gap

## ADDED Requirements

### Requirement: Released products grant a license

A repository that tags releases SHALL keep its license grant in a root `LICENSE`, beside `VERSION`
and `CHANGELOG.md`. A repository that tags no release MAY omit it.

#### Scenario: A releasing repository has no license grant

- **WHEN** the release binding declares release tags and the repository tracks no root `LICENSE`
- **THEN** the paradigm reports the missing license grant

#### Scenario: A repository that never releases has no license grant

- **WHEN** a governed repository declares no release tags and tracks no root `LICENSE`
- **THEN** the paradigm reports no license gap
