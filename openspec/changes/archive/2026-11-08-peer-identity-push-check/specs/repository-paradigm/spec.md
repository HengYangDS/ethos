## ADDED Requirements

### Requirement: Marker edits in record roots reproduce what they replace

Commit validation SHALL judge, without a key, each changed line under an effective record root that
introduces a peer marker: the line SHALL pair one to one with a removed line of the same hunk whose
literal pieces it keeps in order, each marker over one admitted span and each closed-context number
over a digit run that differs only by a number in its range. A marker line without a pair, a
malformed marker and a marker equal to the plain or empty-key digest of its pre-image SHALL refuse.

#### Scenario: A redaction pairs

- **WHEN** a commit replaces the peer identity in a record line with markers and keyed numbers
- **THEN** commit validation admits it

#### Scenario: A marker line has nothing to pair

- **WHEN** a commit adds a marker line in a new file, or changes the words around a marker
- **THEN** commit validation refuses with `record_marker_unpaired`

#### Scenario: A marker is not keyed or not well formed

- **WHEN** a marker equals the plain SHA-256 or the empty-key HMAC of its pre-image, or a token ends
  like a marker but is none
- **THEN** commit validation refuses with `record_marker_unkeyed` or `record_marker_malformed`

#### Scenario: No profile of the range reads

- **WHEN** neither the incumbent baseline's profile nor the proposed head's can be read
- **THEN** commit validation refuses with `record_roots_unread`
