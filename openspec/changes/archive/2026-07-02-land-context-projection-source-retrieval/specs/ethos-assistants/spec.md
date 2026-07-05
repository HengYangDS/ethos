## ADDED Requirements

### Requirement: Source-Verified Assistant Search

ETHOS SHALL expose assistant search and context bundle projection from verified repository spans.

#### Scenario: Stale retrieval candidates are suppressed

- **WHEN** a retrieved candidate no longer matches its file digest, line span, or content digest
- **THEN** ETHOS excludes it from the main context bundle
- **AND** reports the stale candidate in diagnostics instead of promoting it to authority.
