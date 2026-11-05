## ADDED Requirements

### Requirement: Status names the holder's Lease

The status result SHALL name the current Work Lane's Lease generation, expiry and remaining time in its inline summary, also when its detail moves to an artifact. With less than two hours left, status SHALL name the renewal preview as its next action after any repair of its runtime, commit policy or authority, and the resumption preview once the Lease has expired.

#### Scenario: The status detail moves to an artifact

- **WHEN** a holder's status result exceeds its payload budget
- **THEN** its inline summary still names the Lease generation, expiry and remaining time

#### Scenario: The Lease is close to expiry

- **WHEN** less than two hours of the current Work Lane's Lease remain
- **THEN** status names the renewal preview as its next action
- **AND** once the Lease has expired, it names the resumption preview instead

### Requirement: A Lease renewal previews from the current Lease

Lease renewal and resumption without coordinates SHALL preview from the current Work Lane's Lease and name the exact apply command. An apply SHALL bind the lane ref, holder ref, generation and expiry, and SHALL refuse without them.

#### Scenario: A renewal without coordinates

- **WHEN** the holder previews a renewal without Lease coordinates
- **THEN** the preview plans the exact operation on the current Lease
- **AND** it names the apply command with lane ref, holder ref, generation and expiry
- **AND** an apply without those coordinates refuses with `lease_coordinates_required`
