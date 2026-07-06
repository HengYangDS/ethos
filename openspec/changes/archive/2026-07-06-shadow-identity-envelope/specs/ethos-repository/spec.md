## MODIFIED Requirements

### Requirement: Executable Capability Parity Ledger

ETHOS SHALL expose product migration parity as machine-readable command output.

#### Scenario: Shadow parity records input identity

- **WHEN** `ethos parity shadow --adopter <adopter> --target <repo> --execute --json` runs
- **THEN** the shadow parity report includes an `identity` envelope with target
  root, target HEAD, product HEAD, changed paths, compared command identities,
  and evidence input digests
- **AND** tracked parity evidence persists that identity envelope
- **AND** the shadow parity schema rejects reports that omit the identity
  envelope.
