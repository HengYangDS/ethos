## MODIFIED Requirements

### Requirement: Projection authority remains bounded

ETHOS SHALL treat the terminal projection declaration as a lossless selection
and export boundary, not as product or effect authority. A projection SHALL
preserve source identity, semantic owner, current path, relations, validity,
and absence reason through physical topology changes.

#### Scenario: unsafe or incomplete declarations fail closed

- **WHEN** a declaration claims repository-effect authority, a selected source
  is missing or stale, provenance names an unknown source, a relation endpoint
  is unknown, or a semantic item has zero or multiple projection dispositions
- **THEN** export SHALL fail before producing a ProjectionInput
- **AND** no renderer, projection consumer, or generated artifact SHALL mint
  authority or write back into ETHOS

#### Scenario: A source document or module moves

- **WHEN** a governed source moves from one semantic path to another
- **THEN** every selected projection SHALL be regenerated from the new source
  identity and exact tree
- **AND** stale links, stable paths, generated copies, imports, and command
  examples SHALL be reported before acceptance
- **AND** the old path SHALL be deleted unless it remains a proven historical
  carrier with no current authority

#### Scenario: A projection cannot represent the source relation

- **WHEN** a renderer or generated surface drops owner, relation, scope,
  provenance, or validity information
- **THEN** projection proof SHALL block with the missing relation and source
- **AND** presentation convenience SHALL not justify a second semantic carrier
