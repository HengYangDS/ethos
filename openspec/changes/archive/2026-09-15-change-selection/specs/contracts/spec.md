## ADDED Requirements

### Requirement: Change Identity Is Distinct From Capability Identity

ETHOS SHALL resolve accepted Change intent in the official Change namespace.
A canonical capability with the same identifier SHALL neither replace that
intent nor prevent recovery from its applicable exact archive-effect evidence.

#### Scenario: Active Change and capability share an identifier

- **WHEN** an active Change has the same identifier as a canonical capability
- **THEN** intent compilation selects the Change rather than the specification.

#### Scenario: Same-name Change has been officially archived

- **WHEN** the Change is absent from active intent and applicable archive-effect evidence exists
- **THEN** source proof and accepted closeout recover the same exact acceptance without renaming either entity.

#### Scenario: No applicable archived Change exists

- **WHEN** only a same-name specification exists without applicable archive-effect evidence
- **THEN** compilation rejects the missing Change instead of accepting the specification.

#### Scenario: Current Change projection is invalid

- **WHEN** a successful Change query returns incomplete or inconsistent acceptance
- **THEN** compilation rejects that projection without substituting older intent.
