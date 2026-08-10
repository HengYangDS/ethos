## ADDED Requirements

### Requirement: terminal retirement receipt

A linked-lane retirement invoked from the target worktree SHALL observe postconditions from a surviving repository control root after deleting the target worktree. When Lease, ref, and worktree are absent, the command SHALL return a passing terminal receipt.

#### Scenario: linked lane is retired from its own worktree

- **WHEN** the public retirement command removes the target worktree, ref, and Lease
- **THEN** postconditions are observed from a surviving control root and the command emits a passing terminal receipt

### Requirement: durable runtime wheel provenance

An installed package-only runtime SHALL retain a content-addressed local wheel path whose bytes match the manifest wheel SHA256. Reinstallation and lane creation SHALL validate that path without requiring the source checkout or a deleted staging directory.

#### Scenario: a package-only runtime materializes its successor

- **WHEN** the original build staging directory is absent
- **THEN** runtime installation uses the durable content-addressed wheel with matching bytes
