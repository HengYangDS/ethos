## MODIFIED Requirements

### Requirement: Product migration parity is machine-readable
ETHOS SHALL expose product migration parity as machine-readable command output.

#### Scenario: Shadow parity records input identity
- **WHEN** `ethos parity shadow --adopter <adopter> --target <repo> --execute --json` runs
- **THEN** the shadow parity report includes an `identity` envelope with target
  root, target HEAD, product HEAD, changed paths, compared commands, command
  identities, and evidence inputs
- **AND** tracked parity evidence persists that identity envelope
- **AND** the shadow parity schema rejects reports that omit the identity

#### Scenario: Shadow parity rejects external false negatives
- **GIVEN** an embedded fallback command reports a blocking required gap
- **WHEN** the external ETHOS product omits that required gap or only reports it
  as advisory
- **THEN** shadow parity reports a blocking `shadow_false_negative:<command>` gap
- **AND** tracked parity evidence cannot close adopter retirement parity unless
  it records zero false negatives
