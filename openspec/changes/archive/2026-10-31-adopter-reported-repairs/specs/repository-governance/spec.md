## MODIFIED Requirements

### Requirement: An unlanded archive returns to its pre-archive head

Until its Work Lane lands, the Lease holder SHALL be able to compensate an attested archive commit
at the exact archived HEAD that no recorded publication selects. One Lease-bound compare-and-swap
SHALL restore the archive commit's parent, and the index and worktree SHALL then match that parent.
Compensation SHALL be attested and SHALL NOT create another intent, proof or archive authority.

#### Scenario: A failed archived-head proof returns

- **WHEN** the archived HEAD's proof fails and the holder compensates at that exact HEAD
- **THEN** the lane ref, index and worktree equal the pre-archive HEAD
- **AND** the active Change is available again for repair and a later archive
- **AND** the compensation is recorded as one attested Git effect

#### Scenario: An inexact or landed archive is refused

- **WHEN** the HEAD is not an attested archive of the named Change, is contained in the candidate
  branch, the worktree is dirty, the expected HEAD differs or another actor holds the Lease
- **THEN** compensation is refused before any ref, index or worktree effect

#### Scenario: A published archive is refused

- **WHEN** a peer's latest recorded publication selects the archived HEAD as a proposal
- **THEN** compensation is refused before any ref, index or worktree effect
- **AND** the next action retires that proposal while the Work Lane still retains the HEAD

#### Scenario: An interrupted compensation completes

- **WHEN** the compensating ref update completed but the index and worktree still hold the archived
  tree
- **THEN** repeating the same compensation restores them without a second ref update
