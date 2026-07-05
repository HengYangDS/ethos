## ADDED Requirements

### Requirement: Assistant Context Retrieval Commands

ETHOS CLI SHALL expose assistant search, context, context-index, context-purge, and context-eval commands as projection surfaces.

#### Scenario: Context commands report projection boundaries

- **WHEN** an assistant context retrieval command emits JSON
- **THEN** the payload includes query or lifecycle diagnostics
- **AND** declares the projection boundary below repository source, tests, schemas, docs, claims, and evidence.
