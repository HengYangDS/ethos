## ADDED Requirements

### Requirement: Rebuildable Context Index

ETHOS SHALL store assistant retrieval indexes in ignored local state that is rebuildable from repository truth.

#### Scenario: Index lifecycle is local and purgeable

- **WHEN** the context index is built, queried, evaluated, or purged
- **THEN** the command reports manifest, source, and verification metadata
- **AND** no indexed row becomes repository truth or proof evidence by itself.
