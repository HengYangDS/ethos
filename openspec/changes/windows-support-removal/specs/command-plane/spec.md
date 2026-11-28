## MODIFIED Requirements

### Requirement: Git signature trust observations are line-ending portable

ETHOS SHALL recognize an otherwise valid Git SSH signature status independent
of whether the host emits LF or CRLF line endings, while malformed or
unsuccessful verification remains untrusted.

#### Scenario: Git emits a valid CRLF signature status

- **WHEN** Git successfully verifies an object and emits the trusted SSH status
  with CRLF line endings
- **THEN** ETHOS records the same principal and fingerprint as for LF output
- **AND** no signature trust gap is reported.

#### Scenario: Verification output is not a valid terminal status

- **WHEN** Git fails verification or the successful output does not contain the
  complete trusted SSH status
- **THEN** ETHOS reports the corresponding typed signature gap
- **AND** does not infer trust from a partial or malformed line.

### Requirement: Git trust anchors use native host protection

ETHOS SHALL admit external Git trust anchors only when native host authorization protects the anchor
and parent from untrusted modification. Created anchors SHALL meet the same contract. Failed
establishment SHALL retain the bounded host reason.

#### Scenario: POSIX anchor is owner-protected

- **WHEN** a trust anchor and its parent are not writable by group or other identities under the
  POSIX permission model
- **THEN** ETHOS admits the protection fact
- **AND** preserves the existing signature verification behavior.

#### Scenario: An anchor is writable by another identity

- **WHEN** the anchor or its parent is writable by group or other identities
- **THEN** ETHOS reports `git_object_trust_anchor_unprotected`
- **AND** does not infer protection from successful signature verification alone.

#### Scenario: Protection cannot be established

- **WHEN** the host refuses to restrict a created anchor or its directory
- **THEN** ETHOS fails closed with `git_object_trust_anchor_protection_failed`
- **AND** preserves the host's bounded reason.
