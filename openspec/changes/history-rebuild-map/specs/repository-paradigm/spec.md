## MODIFIED Requirements

### Requirement: OpenSpec carries the common rules

Every governed repository that tracks OpenSpec artifacts SHALL select the `spec-driven` schema in
`openspec/config.yaml`, and each artifact's rules SHALL begin with the common rules that the
paradigm contract holds. Repository-specific rules SHALL only follow those common rules. The
paradigm contract's OpenSpec table SHALL also declare `rebuild.toml` as the one Change-local record
that ETHOS reads in a Change's directory beside its official artifacts.

#### Scenario: The common task rule is missing

- **WHEN** a repository configuration omits the common tasks rule
- **THEN** the paradigm reports the missing common rule.

#### Scenario: Repository rules come before the common rules

- **WHEN** a configuration lists only its own proposal rule, in a flow sequence
- **THEN** the repair rewrites the proposal rules as a block sequence that begins with the common
  rules and keeps the repository's rule after them, leaving every other key and comment unchanged.

#### Scenario: A repository selects its own schema

- **WHEN** a configuration selects a schema other than `spec-driven`
- **THEN** the paradigm reports the schema, and the repair leaves that gap report-only.

#### Scenario: A repository tracks no OpenSpec artifact

- **WHEN** a repository tracks no path under `openspec/`
- **THEN** the paradigm reports no OpenSpec gap.

#### Scenario: A Change carries a rebuild record

- **WHEN** a Change's directory holds `rebuild.toml`, whose entries are digests and no markers
- **THEN** ETHOS reads it as that Change's declared record
- **AND** the Change lands and archives without `record_marker_unpaired`

### Requirement: Peer identity markers are keyed, canonical and shared

ETHOS SHALL define one grammar for protected peer identity: the occurrence kinds `url`, `scp`,
`authority` and bare `host`; the marker `<hex32>.<hex32>.private-peer.invalid`, one HMAC-SHA-256 of
a NUL-joined pre-image of version, kind, host, port and path that never hashes scheme or userinfo;
and keyed replacement of project IDs and ports in named closed contexts. Every reader of markers and
every rebuild SHALL use its one left-to-right scan, which a rebuild record extends only as data.

#### Scenario: A URL becomes one marker

- **WHEN** a fed host with a port and a namespace path appears after `//` with userinfo
- **THEN** the host, port and whole leading segments become one marker
- **AND** the scheme, the userinfo and the rest of the line stay byte-identical

#### Scenario: An scp form keeps its colon

- **WHEN** a fed host appears as `git@<H1>:<F1>`
- **THEN** it becomes `git@<marker>:<marker>`, the path a standalone `path` marker
- **AND** the `scp` and `url` markers of the same parts differ

#### Scenario: A key that cannot key refuses

- **WHEN** the key is not 64 lowercase hex characters with at most one trailing newline, or is all
  zero
- **THEN** the reader refuses with `redaction_key_invalid` and nothing is written

#### Scenario: A number in a closed context is replaced

- **WHEN** a fed project ID or port appears in a closed context
- **THEN** it is replaced by a keyed number in its range that differs from the original, every other
  replacement and every fed value and is absent from the domain
- **AND** more than 4,096 probes refuses with `numeric_replacement_exhausted`

#### Scenario: A rebuild record adds data, not grammar

- **WHEN** a rebuild record declares typed spans and merge-request citations, and IDs whose contexts
  it names from the named context set
- **THEN** the shared grammar matches them as data
- **AND** the rebuild matches no occurrence through a grammar of its own, and the record declares no
  context frame

#### Scenario: Every reader uses the one scan

- **WHEN** the redaction verb, the push check, the keyless verifier or a rebuild reads a line
- **THEN** each uses the one left-to-right scan, which takes the longest declared entry of the
  applicable form at each position and never rescans its output
- **AND** each named context pattern matches what it matched before it was named

#### Scenario: A context an adopter needs joins the named set

- **WHEN** an adopter's ID occurs in a context that no named pattern matches
- **THEN** that context joins the named set as data with its own test, so every keyless reader and
  the push check match it

#### Scenario: An occurrence gives one result

- **WHEN** an occurrence matches one declared entry, or declared entries cross inside it
- **THEN** the occurrence gives exactly one result

#### Scenario: An encoded path is replaced

- **WHEN** a path that the record declares occurs percent-encoded
- **THEN** that occurrence is replaced as the declared path

#### Scenario: A merge-request citation is one span

- **WHEN** a commit message cites `<path>!<n>` and the record declares that citation
- **THEN** the citation, its `!<n>` included, is replaced as one span

#### Scenario: Digits inside a digest stay

- **WHEN** a declared ID's digits occur inside a hexadecimal digest, or outside every context that
  the record names for that ID
- **THEN** those digits stay unchanged

### Requirement: Marker edits in record roots reproduce what they replace

Commit validation SHALL judge, without a key, each changed line under an effective record root that
introduces a peer marker: the line SHALL pair one to one with a removed line of the same hunk whose
literal pieces it keeps in order, each marker over one admitted span and each closed-context number
over a digit run that differs only by a number in its range. A marker line without a pair outside a
verified rebuilt blob, a malformed marker and an unkeyed marker SHALL refuse.

#### Scenario: A redaction pairs

- **WHEN** a commit replaces the peer identity in a record line with markers and keyed numbers
- **THEN** commit validation admits it

#### Scenario: A marker line has nothing to pair

- **WHEN** a commit adds a marker line in a new file that is no verified rebuilt blob, or changes
  the words around a marker
- **THEN** commit validation refuses with `record_marker_unpaired`

#### Scenario: A marker is not keyed or not well formed

- **WHEN** a marker equals the plain SHA-256 or the empty-key HMAC of its pre-image, or a run of
  hexadecimal labels ends like a marker but is none
- **THEN** commit validation refuses with `record_marker_unkeyed` or `record_marker_malformed`

#### Scenario: No profile of the range reads

- **WHEN** neither the incumbent baseline's profile nor the proposed head's can be read
- **THEN** commit validation refuses with `record_roots_unread`

#### Scenario: A record describes the marker

- **WHEN** a record names the marker's form by placeholder labels, or names its suffix alone
- **THEN** commit validation admits the line

#### Scenario: A rebuilt blob passes on its original

- **WHEN** a judged commit carries a rebuilt blob under an effective record root while the originals
  are present
- **THEN** that blob passes only when, read through the rebuild's bijection, it equals its original
  with exactly the record's declared items replaced: spans by their markers, IDs in a declared
  context by their keyed numbers, followed digests and mapped IDs
- **AND** any other difference, a changed word around a marker included, is judged as before, and
  without the originals the check answers `unknown`

#### Scenario: A marker over an encoded path or a citation pairs

- **WHEN** a commit replaces a percent-encoded path, or a `<path>!<n>` citation, in a record line
  with a marker
- **THEN** commit validation pairs that marker with the removed line and admits the line
