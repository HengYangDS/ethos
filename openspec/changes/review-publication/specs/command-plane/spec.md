## ADDED Requirements

### Requirement: Exact ref update observation is host independent

ETHOS SHALL expose read-only ref-update admission using target ref, proposed
object, previous object, remote and an explicit trusted baseline when required.
The shared owner SHALL report target role, exact introduced range and OpenSpec
tree obligations without requiring a Work Lane Lease or changing repository or
remote state. Observation SHALL not claim repository proof or mutation authority.

#### Scenario: Detached CI observes an unfinished review snapshot

- **WHEN** CI has a detached signed object with active Change artifacts and an explicit review target
- **THEN** the command applies the review obligations from exact Git inputs
- **AND** a missing local Work Lane or Lease does not prevent the observation
- **AND** local refs, files, coordination and remote refs remain unchanged

#### Scenario: The same object targets accepted truth

- **WHEN** the proposed tree has active Change artifacts and the target is accepted or release
- **THEN** the command reports the exact unarchived intent obligation
- **AND** checkout detachment cannot hide or weaken that target role

#### Scenario: Required coordinates cannot be established

- **WHEN** a required prior object, proposed object or new-ref baseline is unavailable
- **THEN** observation returns a non-passing machine result naming the missing coordinate
- **AND** it does not substitute host HEAD, branch spelling or a new intent carrier

#### Scenario: Proposed policy attempts to rename the destination role

- **WHEN** proposed policy changes the role of a destination protected by the observed prior policy
- **THEN** the prior destination obligation still applies
- **AND** a candidate declaration cannot certify its own weaker classification

#### Scenario: Missing facts and known violations coexist

- **WHEN** required intent observation is unavailable
- **THEN** the result remains UNKNOWN with exact missing facts and a read-only diagnostic
- **AND** an independent known destination violation still yields BLOCK
- **AND** neither result authorizes a repository or remote effect
