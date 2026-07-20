## ADDED Requirements

### Requirement: Canonical Persisted Claim Envelope

ETHOS SHALL load every tracked claim under the configured claims root from the
canonical claim envelope containing `[claim]` and `[evidence]`. Historical
records SHALL preserve dated evidence through an explicit freshness mode; a
reader SHALL NOT retain a second top-level change-claim parser or silently
upgrade an undeclared shape at runtime.

#### Scenario: Canonical historical claim is read

- **WHEN** a tracked claim declares canonical claim and evidence sections with
  a valid dated-evidence digest and `mode = "historical"`
- **THEN** ETHOS SHALL report the claim under its declared id
- **AND** ETHOS SHALL verify the dated-evidence digest without requiring its
  historical source head to equal the current head.

#### Scenario: Top-level legacy claim shape is encountered

- **WHEN** a tracked TOML file in the configured claims root lacks a `[claim]`
  envelope
- **THEN** ETHOS SHALL emit `<file-stem>:claim_envelope_missing` as a required
  gap
- **AND** ETHOS SHALL NOT interpret top-level lifecycle, evidence-reference, or
  promotion-target fields as a compatibility format.
