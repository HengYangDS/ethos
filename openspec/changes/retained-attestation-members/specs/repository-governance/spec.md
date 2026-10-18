## MODIFIED Requirements

### Requirement: Attestation lifetimes end with the transition that consumes them

Every Attestation SHALL have exactly one lifetime derived from its predicate and existing bindings:
operation, head, lineage, window or open-predicate. A lifetime SHALL end only on positive evidence
that the set update observes, never on the absence of a branch or ref alone.

#### Scenario: A Work Lane is retired or its branch is absent

- **WHEN** a lane's retirement effect is selected or its branch is missing
- **THEN** its operation members remain while proof admission can resolve archived intent or
  proposal retirement can resolve refresh provenance through them
- **AND** they end together at the first set update that observes that the lane's branch is absent
  and no commit its ref updates name is reachable from a selected commit or a present pre-repair
  object

#### Scenario: A reader of a retired lane's records cannot be observed

- **WHEN** an update cannot observe whether proof admission or proposal retirement still selects a
  retired lane's records
- **THEN** those records remain and the update reports the gap

#### Scenario: An accepted head is superseded

- **WHEN** closeout advances the accepted ref from one commit to a later one
- **THEN** the proof, integration, acceptance and publication records of the earlier commit end once
  no local ref, fully peeled tag, worktree HEAD or declared peer's last publication selects it
- **AND** the current head's proof, acceptance and publication records remain

#### Scenario: A release tag or repair lineage still exists

- **WHEN** a release tag exists, or a governed ref or a declared peer still reaches a pre-repair
  object
- **THEN** its release or repair record remains
- **AND** the record of a kept runtime generation and the starter formation also remain

#### Scenario: A tag or runtime package is no longer observed

- **WHEN** a release tag or a runtime package is missing locally
- **THEN** the release record and every accepted release identity remain
- **AND** a repair record ends only once every pre-repair object it names is absent locally

#### Scenario: Lifetime facts cannot be observed

- **WHEN** an update cannot observe refs, worktrees or pre-repair objects
- **THEN** it removes no member and reports the gap

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
