## MODIFIED Requirements

### Requirement: Direct Source Budget

Source budget SHALL be measured directly from repository files without worker,
replay, shadow, or self-referential admission runtimes. Coordinates SHALL remain
non-compensatory. The native source-budget declaration SHALL own numeric limits.
Python product and test limits SHALL be required; other coordinates SHALL remain
observations unless explicitly bounded. Size SHALL constrain maintenance cost,
not substitute for semantic preservation, behavior, or the quality floor.

#### Scenario: One budget coordinate exceeds its limit

- **WHEN** an explicitly bounded coordinate exceeds its declared limit
- **THEN** `ethos prove --gate source-budget --json` blocks even if other
  coordinates have unused capacity
- **AND** equality with the limit passes that boundary
- **AND** deletion of necessary semantics or tests, formatting compression, and
  relabeling handwritten source as generated content cannot remediate the gap

#### Scenario: No project-total ceiling is declared

- **WHEN** product and test limits are valid and no aggregate limit is declared
- **THEN** all admitted handwritten categories remain measured and reported
- **AND** the aggregate does not acquire an implicit zero, 90000, or legacy limit
- **AND** explicitly declared optional limits remain enforced
- **AND** missing required limits, unknown coordinates, and malformed numeric
  limits fail closed

#### Scenario: Generated output and historical intent are observed

- **WHEN** generated dependency locks, generated architecture output, and archived
  OpenSpec artifacts are present
- **THEN** they are accounted separately from the maintained-source total
- **AND** their handwritten generators, architecture inputs, active OpenSpec,
  documentation, and configuration remain source
- **AND** existing generation, drift, lifecycle, and cleanup checks still apply
