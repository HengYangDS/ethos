## MODIFIED Requirements

### Requirement: Current repository decisions have one resolution owner

ETHOS SHALL resolve current role, actor, Lease, fresh Git facts, selected
official OpenSpec intent, first exact gap, and recovery action once for each
operation. Status, plan, prewrite, hook, and OpenSpec archive surfaces SHALL
consume that typed resolution without reclassifying its authority, gap, next
action, or Commitment. Effect adapters MAY re-observe exact preconditions at
CAS time and SHALL observe the post-effect state, but they SHALL NOT reselect
the operation's intent.

#### Scenario: One missing fact is observed by several surfaces

- **WHEN** status, plan, prewrite, and a hook evaluate the same current repository state
- **THEN** they report the same first machine gap and the same recovery command
- **AND** no surface replaces it with adoption advice, a placeholder, or command-local prose

#### Scenario: A valid Work Lane has current authority

- **WHEN** the invocation actor owns the lane's valid four-field Lease and the official active Change is resolvable
- **THEN** every consuming surface receives the same passing authority and fresh Git facts
- **AND** no historical carrier, transition Attestation, or command-local binding grants additional authority

#### Scenario: Archive planning reuses the selected intent

- **GIVEN** one archive invocation resolves a completed official Change and its Commitment
- **WHEN** archive readiness and the exact Git-effect plan are compiled
- **THEN** both consume that same current resolution
- **AND** neither rereads OpenSpec governance nor reloads Commitment

#### Scenario: Interrupted archive finalization preserves source identity

- **GIVEN** the worktree contains an exact staged official archive post-image while HEAD still contains the active Change
- **WHEN** the archive operation is resumed
- **THEN** the current resolver compiles intent once from that exact source HEAD
- **AND** the effect plan binds the same Commitment before applying exact CAS

#### Scenario: Archive post-observation does not reselect intent

- **WHEN** the admitted archive Git effect completes
- **THEN** ETHOS re-observes the resulting OpenSpec lifecycle to verify the postcondition
- **AND** that post-observation cannot replace the Commitment already bound into the plan
