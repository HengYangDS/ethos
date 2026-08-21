## ADDED Requirements

### Requirement: Hook runtime inspection exposes one exact repair action
The existing hook runtime and status projections SHALL report installed source
identity, expected source identity, currentness, and one deterministic repair
command without requiring digest archaeology.

#### Scenario: stale runtime is observed in an ETHOS repository family
- **WHEN** the installed runtime identity differs from the accepted ETHOS ref identity
- **THEN** the result reports both source commit/tree pairs and the stale-source gap
- **AND** `next_action` is a complete copyable command bound to the current worktree and accepted source checkout

#### Scenario: stale runtime is observed by a package-only installation
- **WHEN** no ETHOS source checkout supplies the runner
- **THEN** expected identity comes from the invoking wheel's immutable build identity
- **AND** `next_action` repairs the current worktree through the existing `ethos hook install` command

#### Scenario: repair completes
- **WHEN** hook installation post-observes a current runtime
- **THEN** the result reports `verdict=pass` with no repair action
- **AND** status, JSON, and hook inspection consume the same runtime binding rather than deriving separate remedies
