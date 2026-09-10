## ADDED Requirements

### Requirement: Native process records preserve resource identity semantics

ETHOS SHALL distinguish a Unix socket inode from a complete filesystem
device/inode identity when consuming native process observation. Valid socket
records SHALL NOT invalidate an otherwise complete scan or fabricate filesystem
references. Filesystem identities and incomplete-observation rejection SHALL
remain owned by the existing process adapter.

#### Scenario: A supervising process owns an unnamed Unix socket

- **WHEN** native observation identifies a Unix socket with a valid inode but
  no filesystem device field
- **THEN** ETHOS accepts that record without inventing a filesystem identity
- **AND** still detects regular files and directories consumed by live processes.

#### Scenario: A resource cannot be identified safely

- **WHEN** a regular file or directory lacks its device/inode pair, a socket
  inode is malformed, or observation reports inaccessible or unknown state
- **THEN** ETHOS rejects the incomplete observation
- **AND** reviewed retirement remains blocked without deleting content.
