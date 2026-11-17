## MODIFIED Requirements

### Requirement: Invocation and editor bindings have distinct remediation

ETHOS SHALL distinguish a missing invocation actor, a different holder, and a missing editor-root
binding so each condition has one accurate public recovery step.

#### Scenario: Invocation actor is absent

- **WHEN** a mutation requires the current Lease holder and the invocation names no actor, by
  `--actor` or by `ETHOS_ACTOR`
- **THEN** ETHOS reports `invocation_actor_missing` with the expected holder
- **AND** the recovery step asks for the executor's own identity and never names the holder as it
- **AND** it does not misreport a different-holder conflict.

#### Scenario: The actor is not the holder

- **WHEN** a mutation requires the current Lease holder and the invocation's actor is another
- **THEN** ETHOS reports `lease_holder_mismatch`
- **AND** the recovery step is the handoff preview that moves the Lease to that actor.

#### Scenario: Valid Lease lacks editor-root input

- **WHEN** the current holder has a valid Lease but required editor-root input
  is absent
- **THEN** ETHOS reports `editor_root_missing`
- **AND** the remediation binds or supplies the current Work Lane editor root
- **AND** it does not recommend starting another lane.
