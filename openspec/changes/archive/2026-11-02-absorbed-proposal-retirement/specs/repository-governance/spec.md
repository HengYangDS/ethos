## ADDED Requirements

### Requirement: Accepted publication names the proposals it absorbed

When a publication of the accepted branch to a peer applies, ETHOS SHALL name each proposal ref on
that peer whose exact tip the published head preserves, judged as proposal retirement judges it,
and SHALL make the retirement probe of exactly those refs on those peers its next action. A peer
whose proposals cannot be listed SHALL be named as unobserved, and the publication's own state and
verdict SHALL NOT depend on the listing.

#### Scenario: Publishing the accepted branch names its absorbed proposals

- **WHEN** an accepted-branch publication applies to a peer that holds a proposal ref whose tip the
  published head preserves
- **THEN** the result lists that ref under the peer
- **AND** its next action is the retirement probe of exactly the listed refs on the listed peers

#### Scenario: Unabsorbed proposals are not named

- **WHEN** a peer's proposal tip is not preserved by the published head
- **THEN** the result does not name that ref
- **AND** a peer without absorbed proposals adds nothing to the next action

#### Scenario: An unreadable listing is reported, not read as empty

- **WHEN** the proposal listing of a peer fails or times out
- **THEN** the result names that peer as unobserved
- **AND** the publication keeps its own state and verdict
