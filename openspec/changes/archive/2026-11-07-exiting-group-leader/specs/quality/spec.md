## ADDED Requirements

### Requirement: An exiting group leader is not a survivor

When signalling an owned process group is refused while its leader still reports running, the
process owner SHALL wait within its reaping grace for the leader to become reapable and then close
the group as an exited group. A refusal that outlasts the grace while the leader still runs SHALL
fail cleanup as a survivor.

#### Scenario: The leader finishes exiting within the grace

- **WHEN** the group signal is refused while the leader still reports running
- **AND** the leader becomes reapable within the grace
- **THEN** cleanup completes and the original interruption remains observable

#### Scenario: The refusal outlasts the grace

- **WHEN** the group signal stays refused and the leader keeps running past the grace
- **THEN** cleanup fails with the refusal
