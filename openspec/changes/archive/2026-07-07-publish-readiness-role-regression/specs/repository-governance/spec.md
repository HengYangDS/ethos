# repository-governance Delta

## MODIFIED Requirements

### Requirement: Read-only readiness respects command-specific transition semantics

Dry-run transition commands MUST expose the readiness semantics of their command
without claiming mutation authorization.

#### Scenario: Publish dry-run remains accepted-root readiness

- **WHEN** an accepted-root checkout runs `ethos publish --json`
- **THEN** ETHOS reports local publication readiness without treating the
  protected root as a normal land mutation target

#### Scenario: Land dry-run remains role-bound

- **WHEN** an accepted-root checkout runs `ethos land --json` without `--closeout`
- **THEN** ETHOS reports `protected_root_mutation`
- **AND** the next action is `ethos land --closeout --json`
