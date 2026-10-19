## MODIFIED Requirements

### Requirement: Active proposals and designs follow their official templates

For every active Change, ETHOS SHALL resolve the artifact outputs and the schema's templates through the official OpenSpec CLI. Each proposal and design SHALL contain every literal heading of its resolved template, in template order and under its template parent. Sections that the template does not name SHALL remain allowed. When template drift is the only blocking governance gap, prewrite SHALL admit the selected Change's drifted proposal and design files, and no other path, for repair.

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

#### Scenario: Drift that strict validation accepts is repairable

- **WHEN** an active Change passes strict validation, its design lacks a template heading, and that drift is the only blocking gap
- **THEN** prewrite in the owning Work Lane admits that design for repair
- **AND** prewrite of any other path reports that path as uncovered

#### Scenario: Another blocking gap keeps the repair closed

- **WHEN** template drift blocks together with another governance gap, such as an unavailable official CLI
- **THEN** prewrite admits no repair and reports the other gap

#### Scenario: Two drifted Changes do not hold each other's repair

- **WHEN** another active Change also lacks a template heading
- **THEN** the selected Change's drifted artifacts are still admitted for repair
