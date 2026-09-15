## ADDED Requirements

### Requirement: One commit integrity admission owner

Native Git hooks, generated commit creation, range admission and CI SHALL consume
one compiled commit policy. A mutable local switch SHALL NOT silently disable
tracked identity or signature obligations. Only the exact introduced range is
checked; admission SHALL report which policy and verification were applied.

#### Scenario: Message hook is bypassed

- **WHEN** an invalid commit reaches push or CI without message-hook admission
- **THEN** the common object/range validator rejects the declared violation

#### Scenario: Existing history is outside integration

- **WHEN** a valid new range follows unrelated historical identity differences
- **THEN** admission evaluates the new range without re-auditing all history

#### Scenario: Observed capability matches enforcement

- **WHEN** status reports commit integrity capabilities
- **THEN** it distinguishes declared constraints, armed transports and actual verification
