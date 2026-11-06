## ADDED Requirements

### Requirement: A rollback across a repaired declaration refuses until restored

Hook activation SHALL probe the target runtime against the root's tree before it pins anything,
whenever `--runtime` names a build other than the invoking one. When the target refuses the tree's
publication declaration, activation SHALL refuse with `runtime_rollback_declaration_repaired` and
leave no effect. The refusal SHALL name restoring the predecessor's declaration in a lane as the
next action.

#### Scenario: A selector-only rollback after the repair

- **WHEN** an operator activates the ROLLBACK runtime on a tree whose declaration the repair changed
- **THEN** activation refuses with `runtime_rollback_declaration_repaired`
- **AND** selectors, hooks and state are unchanged

#### Scenario: A rollback after the restore

- **WHEN** a lane restores the predecessor's declaration and its HEAD contains the accepted tip
- **THEN** activating ROLLBACK on that lane succeeds

### Requirement: Status names the supported rollback

While a ROLLBACK runtime is held, status SHALL name the one supported rollback: the CURRENT runtime
activating it for the root, which reaches the declaration preflight.

#### Scenario: A cutover holds the predecessor

- **WHEN** a cutover holds the predecessor as ROLLBACK
- **THEN** status names the CURRENT runtime's `hook install --root <root> --runtime <ROLLBACK>`
