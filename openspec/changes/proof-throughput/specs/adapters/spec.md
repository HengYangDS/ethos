## MODIFIED Requirements

### Requirement: Lease-backed Lane Start

ETHOS SHALL create a Work Lane from the exact candidate object by default or
an explicitly selected full trusted commit OID. Current repository identity,
commit policy, trust and runtime authority SHALL govern both modes. It SHALL
acquire one Git-common Lease generation and then require official OpenSpec
intent before tracked authoring. Raw Git worktree creation is not governed
Work Lane state because it lacks the Lease relation. An explicit base SHALL
not rewrite candidate, accepted, release or another lane.

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

#### Scenario: An explicit immutable base is selected

- **WHEN** the caller selects a full trusted commit OID different from the current candidate
- **THEN** preview, apply and recovery retain that exact base
- **AND** the native effect creates only the selected lane ref while asserting the observed candidate
- **AND** the native birth reader derives the lane boundary from that same validated effect
- **AND** the current runtime, candidate ref, foreign indexes and leases remain unchanged

#### Scenario: Explicit base trust or identity is invalid

- **WHEN** the base is absent, abbreviated, unsigned, untrusted or violates current explicit attribution
- **THEN** no lane ref, worktree or Lease is created
- **AND** apply rechecks current trust after preparation, without consuming the base's historical policy

#### Scenario: Historical lane startup fails after creation

- **WHEN** native startup fails after this invocation creates owned resources
- **THEN** compensation removes only those exact created resources
- **AND** it retains the original base in recovery and preserves candidate and foreign work
