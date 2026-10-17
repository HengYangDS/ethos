## ADDED Requirements

### Requirement: Active proposals and designs follow their official templates

For every active Change, ETHOS SHALL resolve the artifact outputs and the schema's templates through the official OpenSpec CLI. Each proposal and design SHALL contain every literal heading of its resolved template, in template order and under its template parent. Sections that the template does not name SHALL remain allowed.

#### Scenario: A design omits an official section

- **WHEN** an active Change's design has no `Risks / Trade-offs` heading and its resolved template has one
- **THEN** OpenSpec governance reports the Change, the artifact and the missing heading, and plan and proof are not clean
- **AND** a design that adds `Migration Plan` or its own sections after the official ones has no gap

#### Scenario: A proposal nests a subsection under the wrong parent

- **WHEN** an active proposal places `### New Capabilities` under `## Impact` instead of `## Capabilities`
- **THEN** OpenSpec governance reports the misplaced heading and its template parent

#### Scenario: The resolved template gains a heading

- **WHEN** the template that the official CLI resolves for a Change's schema gains a literal heading
- **THEN** that heading is required of the Change's artifact without a change to ETHOS

### Requirement: Proof requires an archivable Change

Before the gates of a proof run, ETHOS SHALL archive the active Change that the proof selects with the official OpenSpec CLI in a disposable projection of the exact head and SHALL require official strict validation of the resulting specifications. The projection SHALL be removed and the repository tree SHALL remain unchanged.

#### Scenario: A MODIFIED requirement outgrows the archived limit

- **WHEN** an active Change modifies a requirement so that its text has 501 characters
- **THEN** proof fails before any gate runs and names the specification and the requirement
- **AND** the official change validation that passed does not satisfy this requirement

#### Scenario: An archivable Change is proved

- **WHEN** the simulated archive and its strict validation pass
- **THEN** the proof continues to its gates, and no file outside the disposable projection has changed
