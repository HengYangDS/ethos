## ADDED Requirements

### Requirement: Equal dual-remote publication topology

ETHOS SHALL model publication as one local verification/install layer and two
independent remote targets: GitLab with the
`organization_collaboration` role and GitHub with the
`public_distribution` role. Each remote SHALL declare exactly the same
capabilities: `repository`, `ci_cd`, and `publication`; neither role SHALL
imply governance precedence, failover, or replacement of the other.

#### Scenario: complete topology is declared

- **WHEN** `.ethos/release.toml` declares the local layer plus GitLab and
  GitHub remote records
- **THEN** the release-policy report SHALL expose both remote records and their
  equal capability vectors
- **AND** it SHALL preserve their distinct collaboration and distribution roles.

#### Scenario: malformed topology fails closed

- **WHEN** a declared topology lacks either remote, duplicates a remote name,
  or gives either remote a different capability vector
- **THEN** the release-policy report SHALL emit a topology required gap
- **AND** it SHALL not promote a remaining remote to an authority role.

### Requirement: Remote publication admission is branch and target explicit

ETHOS SHALL admit a remote push only when the named remote is declared and the
destination branch is `dev`, `main`, or matches `submit/*`. `candidate/dev`,
every `work/*` branch, arbitrary branches, and undeclared remote names SHALL
be rejected before ordinary proof admission can authorize the push.

#### Scenario: local candidate cannot be pushed

- **WHEN** the pre-push admission receives `candidate/dev` as its destination
- **THEN** it SHALL return
  `publication_candidate_branch_remote_forbidden:candidate/dev`
- **AND** it SHALL retain candidate as a local integration role.

#### Scenario: declared remote receives an accepted branch

- **WHEN** the pre-push admission receives `dev`, `main`, or `submit/*` and a
  declared GitLab or GitHub remote name
- **THEN** remote-target admission SHALL succeed subject to the existing proof
  and ref-topology gates.

#### Scenario: undeclared remote is rejected

- **WHEN** a pre-push request names a remote absent from the topology
- **THEN** it SHALL emit `publication_remote_target_unknown:<name>`.

### Requirement: Publication observations are independent and no-push

`ethos publish` SHALL report GitLab and GitHub availability and tracking facts
independently. It SHALL not push, claim hosted CI, or infer one target's state
from the other.

#### Scenario: one remote is available

- **WHEN** GitLab is unavailable and GitHub is available
- **THEN** publish SHALL expose both observations
- **AND** report a single available target without claiming remote publication.
