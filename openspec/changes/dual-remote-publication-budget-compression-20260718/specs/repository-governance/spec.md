## MODIFIED Requirements

### Requirement: Equal dual-remote publication topology

ETHOS SHALL model publication as one local verification/install layer and two
independent remote targets: GitLab organization collaboration and GitHub public
distribution. Each target SHALL expose equal `repository`, `ci_cd`, and
`publication` capabilities; no target SHALL become a fallback or authority
above the other. Remote admission and hosted CI SHALL allow only `dev`, `main`,
and `submit/*`; `candidate/dev` and every `work/*` branch SHALL remain local.
`ethos publish` SHALL observe declared targets independently without pushing or
claiming hosted CI success. Compact declarations SHALL retain valid former
verbose remote records for adopter compatibility.

#### Scenario: explicit remote admission preserves local candidate isolation

- **WHEN** pre-push admission receives a named declared target and `candidate/dev`
- **THEN** it SHALL reject the destination before proof admission
- **AND** it SHALL emit `publication_candidate_branch_remote_forbidden:candidate/dev`.

#### Scenario: independent remote observations remain no-push

- **WHEN** `ethos publish` observes GitLab and GitHub
- **THEN** it SHALL expose each target separately
- **AND** `remote_push` SHALL remain `not_performed`
- **AND** hosted CI status SHALL remain unclaimed.

#### Scenario: valid verbose declaration remains accepted

- **WHEN** an adopter supplies valid `[[publication.remote]]` records
- **THEN** ETHOS SHALL resolve the same named GitLab and GitHub targets
- **AND** it SHALL retain equal capability and explicit-admission validation.
