## ADDED Requirements

### Requirement: A release binding may name the peer that rehearses its releases

The release binding MAY declare `[release.rehearsal]` with the one key `peer`, whose value SHALL
be the identity of a declared publication peer with the `ci_cd` capability. The paradigm SHALL
report a table with another key, or a peer that the binding does not declare so, as
`release-binding`, and the repair SHALL leave it. A binding without the table SHALL be read for
no rehearsal and SHALL meet no gap for one.

#### Scenario: The table names a declared CI peer

- **WHEN** `.ethos/release.toml` declares `[release.rehearsal]` with `peer` naming a declared peer
  that has the `ci_cd` capability
- **THEN** the paradigm reports no gap for the table
- **AND** the repair of another unread `[release]` key keeps the table.

#### Scenario: The table names no declared CI peer

- **WHEN** the table's `peer` names no declared peer, or one without the `ci_cd` capability, or
  the table holds another key
- **THEN** the paradigm reports `release.rehearsal` as `release-binding`
- **AND** the repair plans no edit for it.

#### Scenario: A binding declares no table

- **WHEN** a release binding that protects release tags declares no `[release.rehearsal]`
- **THEN** the paradigm reports nothing for a rehearsal
- **AND** no command reads a forge for one.
