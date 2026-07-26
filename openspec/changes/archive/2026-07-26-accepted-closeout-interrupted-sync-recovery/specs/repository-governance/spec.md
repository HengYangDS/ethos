## ADDED Requirements

### Requirement: Interrupted accepted-worktree synchronization recovery is receipt-bound

ETHOS SHALL provide one explicit recovery path for a native closeout that
already promoted the accepted ref but failed while synchronizing that same
checkout. The path SHALL not weaken ordinary dirty accepted-root admission or
advance a ref, lease, proof record, SQLite state, retired-resolution record, or
ownerless resolution record.

#### Scenario: Exact interrupted residue is recovered by a current candidate runner

- **WHEN** `ethos land --closeout --recover-accepted-worktree-sync --apply`
  receives authorization, stale-lock and irreversible confirmation, an external
  failed-closeout receipt and SHA-256, an expected promoted accepted head, an
  exact index-lock digest, and an absent external quarantine path
- **THEN** it SHALL require the receipt to record
  `accepted_worktree_sync_failed` for the configured accepted/candidate
  branches and exact prior/promoted heads
- **AND** it SHALL require accepted `HEAD` and the accepted ref to equal the
  receipt's promoted head, while the candidate ref equals that head or is its
  descendant and the index/worktree exactly equal the prior accepted tree with
  no untracked or conflicted content
- **AND** it SHALL relocate only the verified regular lock through an atomic
  no-replace same-filesystem operation, synchronize only the accepted worktree,
  and re-observe clean checkout and unchanged refs
- **AND** it SHALL fail closed if the native no-replace operation is unavailable
  or the quarantine target races into existence.

#### Scenario: Ordinary dirty accepted-root work remains blocked

- **WHEN** an accepted root is dirty but lacks the exact receipt-bound prior
  index/worktree residue, or any receipt/head/digest/fingerprint/quarantine
  binding differs
- **THEN** recovery SHALL block with a specific gap
- **AND** ordinary `ethos land --closeout` SHALL continue to report
  `accepted_root_dirty`
- **AND** no hard reset, quarantine relocation, or ref mutation SHALL occur.
