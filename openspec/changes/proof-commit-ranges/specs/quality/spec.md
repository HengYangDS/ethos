## ADDED Requirements

### Requirement: Full proof validates the next publication's commit ranges

The ETHOS repository's full proof SHALL validate, with the candidate's own source, every commit
that the next accepted and release pushes to a declared peer carry beyond the peer's tracking tip,
with each target's branch-role policy and the configured commit trust anchor. A proof SHALL refuse
when no declared peer is observed.

#### Scenario: A new commit check refuses a published range

- **WHEN** the candidate's commit validation refuses a commit beyond a peer's tracking tip
- **THEN** the full proof fails through the `commit-ranges` gate
- **AND** hosted CI does not become the first observer of that refusal

#### Scenario: No peer is observed

- **WHEN** no declared peer has a tracking tip for the accepted or the release branch
- **THEN** the gate refuses with `commit_ranges_unobserved`
