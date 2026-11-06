## MODIFIED Requirements

### Requirement: Forge review observation uses declared API coordinates

Review observation for a declared GitHub or GitLab peer SHALL run that provider's native client
noninteractively within a bound. It SHALL resolve the peer's web repository from local connection
metadata only, never from tracked configuration. SSH-only coordinates and failed or unavailable
queries SHALL remain unknown, and a plain Git peer has no review system. Neither coordinates nor
client credentials SHALL grant deletion authority.

#### Scenario: A peer is reachable only over SSH

- **GIVEN** a declared GitLab peer with an SSH Git remote and no local key
- **WHEN** publication retirement observes its open reviews
- **THEN** the review state is unknown with reason `forge_repository_unresolved:<name>`
- **AND** its next action is `git config --local remote.<name>.forgeRepository <web-url>`
- **AND** the proposal ref is not deleted.

#### Scenario: A local key names the web repository

- **WHEN** the local `remote.<name>.forgeRepository` holds a valid credential-free web URL
- **THEN** review observation uses it before the Git remote

#### Scenario: An http remote names the web repository

- **WHEN** a peer's Git remote is an `http` or `https` URL without userinfo and no local key exists
- **THEN** review observation uses that URL with its scheme, host and port, without one trailing
  `/` and `.git`

#### Scenario: A credentialed remote refuses

- **WHEN** a peer's Git remote carries userinfo
- **THEN** resolution refuses with `forge_repository_credentialed:<name>` and never repeats the URL
