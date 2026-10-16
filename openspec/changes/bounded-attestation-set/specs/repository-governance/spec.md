## ADDED Requirements

### Requirement: Attestation lifetimes end with the transition that consumes them

Every Attestation SHALL have exactly one lifetime derived from its predicate and existing bindings:
operation, head, lineage, window or open-predicate. A lifetime SHALL end only on positive evidence
that the set update observes, never on the absence of a branch or ref alone.

#### Scenario: A Work Lane is retired

- **WHEN** a lane's retirement effect is selected
- **THEN** the next set update removes that lane's operation members
- **AND** the members of live lanes are unchanged

#### Scenario: A lane branch is absent without a retirement effect

- **WHEN** a lane's branch is missing but no retirement effect for it is selected
- **THEN** its operation members remain

#### Scenario: An accepted head is superseded

- **WHEN** closeout advances the accepted ref from one commit to a later one
- **THEN** the proof, integration, acceptance, archive and publication records of the earlier commit
  end once neither a governed local ref nor a declared peer's last publication selects it
- **AND** the current head's proof, acceptance and publication records remain

#### Scenario: A release tag or repair lineage still exists

- **WHEN** a release tag exists, or a governed ref or a declared peer still reaches a pre-repair
  object
- **THEN** its release or repair record remains
- **AND** the record of a kept runtime generation and the starter formation also remain

#### Scenario: A tag or runtime package store is no longer observed

- **WHEN** a release tag is missing locally, or no runtime package store is observed
- **THEN** the release record and every runtime generation record remain
- **AND** a repair record ends only once every pre-repair object it names is absent locally

#### Scenario: A validity window passes

- **WHEN** a member's `valid_until` has passed
- **THEN** the next set update removes it

#### Scenario: A predicate has no product reader

- **WHEN** a member's predicate has no product lifetime
- **THEN** the member remains until an admitted release removes it

#### Scenario: A needed member has ended

- **WHEN** a transition requires a member that has left the set
- **THEN** the transition fails closed with its existing missing-evidence gap
- **AND** it does not infer the absent member
