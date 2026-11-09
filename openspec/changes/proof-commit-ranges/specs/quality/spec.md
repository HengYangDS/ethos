## ADDED Requirements

### Requirement: Full proof validates the next publication's commit ranges

The ETHOS repository's full proof SHALL validate, with the candidate's own source, every commit
that the next accepted and release pushes carry beyond the tracking tip of each declared peer whose
remote the checkout configures, with the commit policy of each revision and the configured commit
trust anchor. The gate SHALL refuse when no configured peer has a tracking tip, and SHALL pass as
not applicable when the checkout configures no declared peer remote.

#### Scenario: A new commit check refuses a published range

- **WHEN** the candidate's commit validation refuses a commit beyond a peer's tracking tip
- **THEN** the full proof fails through the `commit-ranges` gate
- **AND** hosted CI does not become the first observer of that refusal

#### Scenario: No peer is observed

- **WHEN** the checkout configures a declared peer's remote, and no configured peer has a tracking
  tip for the accepted or the release branch
- **THEN** the gate refuses with `commit_ranges_unobserved`

#### Scenario: A checkout without a peer remote

- **WHEN** the checkout configures no declared peer's remote, as a hosted checkout of `origin` does
- **THEN** the gate passes as not applicable, with the note `commit_ranges_no_peer_remote`
- **AND** the hosted job's `hook commit-range` step keeps validating the actual push
