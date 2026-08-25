## ADDED Requirements

### Requirement: Exact-tree terminal projection input

ETHOS SHALL export its terminal architecture projection input from one exact Git
commit and tree without reading mutable working-tree content.

#### Scenario: deterministic export ignores working-tree drift

- **GIVEN** one selected commit whose declaration, projection documents, and
  semantic sources exist in that tree
- **WHEN** the terminal projection exporter runs twice for that commit while a
  selected working-tree source differs
- **THEN** both outputs SHALL be byte-identical
- **AND** the output SHALL bind the exact commit, tree, repository-relative
  source paths, source digests, projection-document digests, and one content
  digest
- **AND** no host absolute path or wall-clock timestamp SHALL enter the output.

### Requirement: Projection authority remains bounded

ETHOS SHALL treat the terminal projection declaration as a lossless selection
and export boundary, not as product or effect authority.

#### Scenario: unsafe or incomplete declarations fail closed

- **WHEN** a declaration claims repository-effect authority, a selected source
  is missing or stale, provenance names an unknown source, a relation endpoint
  is unknown, or a semantic item has zero or multiple projection dispositions
- **THEN** export SHALL fail before producing a ProjectionInput
- **AND** no renderer, projection consumer, or generated artifact SHALL mint
  authority or write back into ETHOS.
