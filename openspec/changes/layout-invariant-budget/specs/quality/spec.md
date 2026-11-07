## MODIFIED Requirements

### Requirement: Direct Source Budget

Source budget SHALL be measured directly from repository files without worker,
replay, shadow, or self-referential admission runtimes. Coordinates SHALL remain
non-compensatory. The native source-budget declaration SHALL own numeric limits.
Python product and test limits SHALL be required; other coordinates SHALL remain
observations unless explicitly bounded. Size SHALL constrain maintenance cost,
not substitute for semantic preservation, behavior, or the quality floor.
A Python coordinate with a declared tokens-per-line ratio SHALL be enforced in
line-equivalents: its layout-invariant code tokens divided by that ratio, rounded
up. Layout-invariant code tokens SHALL exclude comments, line structure,
standalone string expressions, statement semicolons and a comma directly before a
closing bracket. The physical-line measure SHALL remain the native cross-check's
comparison and the per-file ceiling's measure.

#### Scenario: One budget coordinate exceeds its limit

- **WHEN** an explicitly bounded coordinate exceeds its declared limit
- **THEN** `ethos prove --gate source-budget --json` blocks even if other
  coordinates have unused capacity
- **AND** equality with the limit passes that boundary
- **AND** deletion of necessary semantics or tests, formatting compression, and
  relabeling handwritten source as generated content cannot remediate the gap

#### Scenario: Reformatting does not move an enforced Python coordinate

- **WHEN** a Python file is reformatted without changing its syntax tree, for
  example by joining a wrapped call onto one line and dropping its trailing comma
- **THEN** its layout-invariant code tokens and the enforced line-equivalents of
  its category are unchanged
- **AND** its physical-line measure may change for the cross-check and the
  per-file ceiling

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
