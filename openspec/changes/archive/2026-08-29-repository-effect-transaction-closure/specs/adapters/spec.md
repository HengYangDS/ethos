## MODIFIED Requirements

### Requirement: Lease-backed Lane Start

ETHOS SHALL create a Work Lane from the exact candidate object, acquire one
Git-common Lease generation, and then require official OpenSpec intent before
tracked authoring. Raw Git worktree creation is not governed Work Lane state
because it lacks the Lease relation.

#### Scenario: Work Lane start is applied

- **WHEN** the public command creates a lane from a clean accepted repository
- **THEN** it creates the exact worktree/ref and one Git-common Lease generation
- **AND** it creates no tracked Commitment carrier, Claim boundary, or mirrored Git coordinates

#### Scenario: Existing Change continuation is applied

- **WHEN** work continues in an already owned clean Work Lane
- **THEN** ETHOS retains the same lane and Lease relation and re-observes current Git and OpenSpec facts
- **AND** it copies no intent carrier or repository coordinates

#### Scenario: Work Lane start intent is absent or ambiguous

- **WHEN** a new Work Lane has no active official OpenSpec Change
- **THEN** lane creation remains complete
- **AND** tracked product authoring remains blocked until exactly one official Change exists

#### Scenario: Work Lane start is requested from a non-accepted or dirty root

- **WHEN** lane start runs from an existing Work Lane or dirty accepted root
- **THEN** ETHOS blocks before mutation

### Requirement: Atomic Fresh Change Bootstrap

ETHOS SHALL create a mutation-capable Work Lane and its official OpenSpec Change
through one bounded public transition from clean accepted truth. The Lease SHALL
bind only lane, holder, generation, and expiry; the resulting Git ref and
OpenSpec artifacts SHALL be re-observed as fresh facts.

#### Scenario: A fresh Change starts without a predecessor lane

- **WHEN** an operator supplies a Change name and holder from a clean accepted root with a current clean candidate
- **THEN** ETHOS creates the exact Work Lane and official OpenSpec artifacts
- **AND** no tracked Commitment carrier, predecessor ledger, or Lease mirror is created

#### Scenario: Bootstrap intent is absent or ambiguous

- **WHEN** the Change name, target lane, holder, accepted root, or candidate is missing or ambiguous
- **THEN** ETHOS blocks before the first effect or compensates only its exact owned effects
- **AND** it does not infer intent from an archive, branch name, historical task, or conversation

#### Scenario: A live Change continuation is requested

- **WHEN** an operator continues a valid active Change in its owned Work Lane
- **THEN** ETHOS reuses that lane and official Change
- **AND** the fresh bootstrap path is not also evaluated
