## ADDED Requirements

### Requirement: Source-complete intent context

ETHOS SHALL preserve every unique official context document's repository path,
exact content and content digest in its transient planning projection. It SHALL
report missing, unreadable, invalid or escaping sources instead of silently
omitting them. Native Markdown syntax SHALL determine auxiliary section views.

#### Scenario: Equivalent official Markdown preserves constraints

- **WHEN** non-goals or open questions use bullet, ordered, wrapped or paragraph forms
- **THEN** the context retains their complete text and exact source content
- **AND** fenced headings do not create real sections and peer headings end sections

#### Scenario: An observed source cannot be consumed

- **WHEN** the official context names an unavailable, invalid or escaping source
- **THEN** the result identifies that source gap and does not claim complete context
- **AND** source observation does not authorize reading outside the repository

#### Scenario: Duplicate paths do not create duplicate evidence

- **WHEN** multiple official artifact roles refer to the same document
- **THEN** the document is read once and represented once in deterministic path order
- **AND** its repeated reference does not imply independent supporting evidence

### Requirement: Structural compilation does not certify interpretation

ETHOS SHALL distinguish source preservation and structural compilation from
acceptance of an interpretation, sufficient verification, admitted effects and
achieved user outcomes. The repository handoff procedure SHALL require relevant
source constraints to be retained, explicitly excluded by an authorized decision
or marked unresolved before claiming intent alignment.

#### Scenario: The zero-winner requirement is mistranslated

- **WHEN** the source permits all candidates to be dropped with useful results preserved
- **AND** a candidate interpretation requires exactly one winner
- **THEN** both original constraint and candidate interpretation remain available for review
- **AND** successful parsing or compilation does not certify that interpretation
- **AND** an Agent following the handoff procedure rejects the added winner obligation

#### Scenario: Cooperation and dropping do not imply destruction

- **WHEN** compatible contributions are combined or no competing candidate is selected
- **THEN** the accepted intent may select multiple cooperative contributions or zero competing winners
- **AND** dropping integration does not authorize loss of useful conclusions or unique results
