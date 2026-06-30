## ADDED Requirements

### Requirement: Executable Capability Parity Ledger
ETHOS SHALL expose product migration parity as machine-readable command output.

#### Scenario: Parity ledger is emitted
- **WHEN** `ethos parity ledger --json` runs
- **THEN** every tracked capability has source location, target home,
  disposition, required tests, parity criterion, and rollback impact
- **AND** the unclassified capability count is zero

#### Scenario: Adopter parity gaps are reported
- **WHEN** `ethos parity gaps --adopter <name> --json` runs
- **THEN** ETHOS reports pending product migration gaps and an adopter shadow
  parity gap without mutating the adopter repository

### Requirement: Fast Daily Governance Checks
ETHOS SHALL keep daily proof and report commands fast while preserving explicit
deep OpenSpec validation.

#### Scenario: Daily proof avoids deep OpenSpec
- **WHEN** `ethos prove --json` runs without `--full`
- **THEN** self-audit uses OpenSpec shape mode
- **AND** official OpenSpec validation remains available through deep commands
