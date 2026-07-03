## MODIFIED Requirements

### Requirement: Explicit mutation context contract

ETHOS SHALL define mutation-capable operations with explicit target-root,
checkout-role, editor-root, target-path, hook-layer, command-risk, and
admission-result fields.

#### Scenario: Mutation context is auditable

- **WHEN** a mutation-capable operation is admitted, blocked, or fused
- **THEN** the machine result includes target root, editor root, branch role,
  target paths, hook layer when applicable, decision, and required gaps
- **AND** pre-run hook results include command risk classification.
