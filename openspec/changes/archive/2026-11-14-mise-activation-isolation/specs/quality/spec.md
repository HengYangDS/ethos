## ADDED Requirements

### Requirement: Locked execution inherits no mise activation state

A child that ETHOS starts to resolve or to run locked tools SHALL inherit neither the caller's
`MISE_` variables nor the state that a shell's mise activation exports under `__MISE_`. One
declaration at the Mise adapter SHALL name both families, and every such child SHALL be started
with it, so that the same repository, head and runtime give the same result from an activated
shell, a clean shell and a hosted job.

#### Scenario: A proof is launched from a shell that activated mise

- **WHEN** the launching environment carries `__MISE_DIFF` and a gate's child runs `mise exec`
- **THEN** the child's environment holds no `__MISE_` variable and only the `MISE_` variables that
  ETHOS sets
- **AND** the nested command resolves the locked tool, as it does from a clean shell

#### Scenario: A new child of the Mise adapter is added

- **WHEN** a call site starts a child that resolves or runs locked tools
- **THEN** it removes the families the adapter declares, not a literal of its own
