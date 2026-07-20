## MODIFIED Requirements

### Requirement: Workflow Runtime Contract
ETHOS SHALL define workflow runtime contracts as provider-neutral schemas and
TOML declarations over derived repository facts. Event entities are admitted
only when a tracked production path creates them and a tracked consumer,
reducer, or evidence boundary uses them.

#### Scenario: Workflow contract is inspected
- **WHEN** ETHOS validates `system/workflows.toml`
- **THEN** the contract exposes lifecycle states, transitions, guard names, required facts, node kinds, enforcement modes, run-state locality, handoff locality, and eval metrics
- **AND** it does not expose a declaration-only event stream, event count, or event-locality field
- **AND** every transition references declared states and guards
- **AND** every blocking invalid-state reference maps to the ETHOS invalid-state taxonomy
- **AND** no workflow contract requires `.comet`, `.taskmaster`, `.specify`, or another external runtime store as authority
