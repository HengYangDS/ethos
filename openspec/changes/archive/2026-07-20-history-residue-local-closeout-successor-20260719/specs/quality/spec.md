## ADDED Requirements

### Requirement: History-residue closeout removes every active campaign growth overage

The system SHALL settle the successor's live source-budget overages through real
carrier deletion or consolidation without changing baseline, active limit,
debt, expiry, or terminal-target values.

#### Scenario: All active category limits pass

- **WHEN** the successor reaches its final authoring HEAD
- **THEN** `python_product` is at most 35675
- **AND** `python_tests` is at most 46865
- **AND** `python_total` is at most 84024
- **AND** `shell` is at most 1552
- **AND** `toml` is at most 11633
- **AND** `ethos quality source-budget --json` reports no campaign growth overage

#### Scenario: Local settlement does not overclaim terminal completion

- **WHEN** all active campaign growth overages are absent
- **THEN** the successor MAY claim local category settlement
- **BUT** it SHALL NOT claim global campaign terminal completion unless `terminal_target_met=true` and active debt is zero
