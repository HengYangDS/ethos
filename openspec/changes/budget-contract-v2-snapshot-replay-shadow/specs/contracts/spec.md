## ADDED Requirements

### Requirement: Public Source And Snapshot Byte Measurement

ETHOS SHALL expose public source/bytes measurement boundaries so immutable Git
objects and ordinary files use one canonical semantic implementation.

#### Scenario: Existing file APIs delegate to public bytes/source APIs

- **WHEN** a caller measures ELOC from source text or measures a classified
  carrier or complete snapshot from already-admitted bytes
- **THEN** `effective_code_lines_for_source(source)` SHALL own ELOC parsing and
  path-based ELOC SHALL delegate after reading text
- **AND** `measure_carrier_bytes(...)` and `measure_snapshot_bytes(...)` SHALL
  own native carrier/snapshot measurement over direct bytes
- **AND** existing path APIs SHALL read once and delegate to those public APIs
- **AND** immutable replay SHALL NOT import a private content helper or duplicate
  a parser/normalizer implementation.

### Requirement: Immutable Git Tree Snapshot Load

ETHOS SHALL load a selected historical snapshot from immutable Git objects
without creating or mutating a checkout or worktree.

#### Scenario: A treeish resolves before any selected blob content is read

- **WHEN** `tree_snapshot(root, treeish)` is requested
- **THEN** ETHOS SHALL peel the treeish to one full commit SHA and its full tree
  SHA before exposing entries
- **AND** it SHALL parse one strict recursive full-tree NUL-framed `git ls-tree`
  stream with canonical mode, type, OID, path, uniqueness, and order
- **AND** repository-relative paths SHALL be normalized, non-empty, and free of
  NUL, traversal, absolute, symlink, gitlink, or unsupported-mode semantics
- **AND** malformed framing, invalid mode/type/OID/path, duplicate or unordered
  entries, command failure, or missing identity SHALL return no partial load.

#### Scenario: Selected blobs use one strict batch exchange

- **WHEN** a validated snapshot inventory selects blob OIDs
- **THEN** ETHOS SHALL send the selected OIDs once, in inventory order, to one
  `git cat-file --batch` process
- **AND** every response SHALL match requested OID, blob type, declared size,
  exact payload length, separator, and response order
- **AND** missing objects, unexpected types, truncation, extra/trailing data,
  non-zero exit, or any read/close failure SHALL return no partial bytes,
  measurements, or snapshot digest.

#### Scenario: Worktree snapshot is clean HEAD only

- **WHEN** `worktree_snapshot(root)` is requested
- **THEN** ETHOS SHALL reject tracked, staged, conflicted, ignored-admission, or
  untracked dirt before delegating to immutable HEAD commit/tree objects
- **AND** it SHALL NOT read mutable worktree carrier content as snapshot truth.
