## MODIFIED Requirements

### Requirement: Agent projections preserve native Change ownership

OpenSpec SHALL alone own Change intent, design, specs and progress. Commitment SHALL remain
transient; skills SHALL remain optional projections. ETHOS SHALL NOT retain a skill that owns or
redescribes the native Change lifecycle. Public ETHOS commands SHALL remain independent capabilities
selected by current results, not a sequence owned by an agent projection.

#### Scenario: Change lifecycle retains one owner

- **WHEN** the repository exposes agent skills and public ETHOS commands
- **THEN** OpenSpec remains the sole owner of Change authoring, progress, validation, and archive
- **AND** no ETHOS skill or current document reifies the public command catalog as a second Change
  lifecycle

#### Scenario: Official Change planning remains writable

- **WHEN** one active official Change has generated some but not all of its declared planning
  artifacts and a partial Commitment is already compilable
- **THEN** prewrite admits only the still-declared official artifact outputs needed to complete that
  Change, and that Change's declared `rebuild.toml`
- **AND** the partial Commitment does not turn incomplete planning into a self-blocking state or
  authorize unrelated product paths
