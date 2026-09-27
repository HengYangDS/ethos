# Repository Governance Delta

## ADDED Requirements

### Requirement: Blocking Canonical Guidance Has a Repair Path

ETHOS SHALL admit corrective prewrite for an existing canonical OpenSpec spec named by a current, valid official spec INFO finding when repository policy blocks that finding. The admission SHALL retain the selected Change, actor, Lease, runtime, and exact-path boundaries. It SHALL not satisfy ordinary proof or commit admission.

#### Scenario: Exact canonical repair is reachable

- **WHEN** current official validation reports a valid canonical spec with a blocking INFO finding and the owning Work Lane requests prewrite for its existing `openspec/specs/<capability>/spec.md`
- **THEN** ETHOS admits that exact path so the finding can be removed
- **AND** ordinary proof remains blocked until fresh validation no longer reports the finding.

#### Scenario: Unrelated or unsupported paths gain no authority

- **WHEN** the request includes an unrelated path, a missing or symlinked canonical spec, a mismatched finding, an invalid report envelope, or an INFO finding only on an active Change
- **THEN** that finding grants no corrective prewrite for the unsupported path.

#### Scenario: Blocked status selects a repair action

- **WHEN** canonical INFO is the first blocking gap for a coordinated Work Lane
- **THEN** status names a prewrite action for one exact affected canonical spec rather than another status observation.
