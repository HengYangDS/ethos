## ADDED Requirements

### Requirement: Git signature trust observations are line-ending portable

ETHOS SHALL recognize an otherwise valid Git SSH signature status independent
of whether the host emits LF or CRLF line endings, while malformed or
unsuccessful verification remains untrusted.

#### Scenario: Windows emits a valid CRLF signature status

- **WHEN** Git successfully verifies an object and emits the trusted SSH status
  with CRLF line endings
- **THEN** ETHOS records the same principal and fingerprint as for LF output
- **AND** no signature trust gap is reported.

#### Scenario: Verification output is not a valid terminal status

- **WHEN** Git fails verification or the successful output does not contain the
  complete trusted SSH status
- **THEN** ETHOS reports the corresponding typed signature gap
- **AND** does not infer trust from a partial or malformed line.

### Requirement: Package smoke preserves publication failure facts

The installed-package smoke owner SHALL expose the exact publication required
gaps when the expected full-ref transition plan is unavailable.

#### Scenario: Publication planning is blocked

- **WHEN** the installed CLI returns no full-ref compare-and-swap effect or
  reports a publication topology or source gap
- **THEN** package smoke fails with the exact required gaps and command context
- **AND** does not replace them with only a generic unavailable-plan message.
