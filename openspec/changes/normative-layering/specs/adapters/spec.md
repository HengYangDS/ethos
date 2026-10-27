## ADDED Requirements

### Requirement: Forge review observation uses declared API coordinates

Review observation for a declared GitHub or GitLab peer SHALL run that
provider's native client noninteractively within a bound, against the peer's
credential-free HTTP(S) `forge_repository`, else its local
`remote.<name>.forgeRepository`, else an HTTP Git URL. SSH-only coordinates and
failed or unavailable queries SHALL remain unknown; a plain Git peer has no
review system. Neither coordinates nor client credentials SHALL grant deletion
authority.

#### Scenario: A peer is reachable only over SSH

- **GIVEN** a declared GitLab peer with an SSH Git remote and no API coordinates
- **WHEN** publication retirement observes its open reviews
- **THEN** the review state is unknown with reason `forge_repository_required`
- **AND** the proposal ref is not deleted.
