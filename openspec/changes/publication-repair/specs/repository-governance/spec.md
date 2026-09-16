## MODIFIED Requirements

### Requirement: Publication composes historical repair with forward integration

ETHOS SHALL recognize a completed exact historical repair followed by native
ancestor-related commits when the selected peer still holds that repair's exact
source ref. The existing range owner SHALL validate only the forward range under
its baseline and proposed policies. Proposed-object proof, accepted effect and
remote CAS remain independent requirements.

#### Scenario: Signed forward commits follow a verified replacement

- **WHEN** the peer ref equals the recorded repair source and proposed accepted
  descends from its verified replacement
- **THEN** publication recognizes the historical segment as repaired
- **AND** the common commit-policy owner checks replacement-to-proposed commits
  without scanning the repaired historical segment as new integration

#### Scenario: A forward commit violates policy

- **WHEN** a descendant has an invalid subject, identity or required signature
- **THEN** range admission rejects that descendant despite valid repair provenance

#### Scenario: Repair provenance does not establish the requested relationship

- **WHEN** the ref or old object differs, replacement ancestry is absent, repair
  evidence is missing, or multiple repair candidates remain ambiguous
- **THEN** that request is not admitted as a repaired-history publication
- **AND** no remote or local ref is changed by the observation

#### Scenario: Accepted publication consumes the verified forward baseline

- **WHEN** public pre-push or publication evaluates accepted descendants after
  a verified repair of the peer's exact old object
- **THEN** the accepted topology check evaluates forward ancestry from the
  verified replacement while still requiring the current candidate head
- **AND** proposed-object proof and its accepted effect remain required
- **AND** each peer applies only its observed old-to-proposed ref transaction

#### Scenario: Repaired ancestry cannot excuse missing current acceptance

- **WHEN** the repair relation is valid but current proof, accepted effect or
  candidate equality is absent
- **THEN** publication is rejected without changing either peer

## ADDED Requirements

### Requirement: Native hook decisions preserve JSON evidence

ETHOS SHALL emit a JSON-native rejection for failed native Git hook admission,
preserving valid nested immutable evidence, required gaps and continuation.
Invalid evidence values SHALL produce a stable blocked transport result rather
than a traceback or fabricated success. Successful native hooks SHALL retain
quiet zero-exit behavior.

#### Scenario: Rejected report contains immutable proof values

- **WHEN** pre-push rejects or cannot determine admission and carries nested
  immutable Attestation or Commitment mappings and ordered collections
- **THEN** stderr contains one valid JSON report with the original verdict,
  required gaps, evidence and next action
- **AND** the original immutable values remain unchanged

#### Scenario: Evidence cannot be represented as JSON

- **WHEN** a failed hook report contains unsupported or nonfinite values
- **THEN** the hook exits nonzero with `hook_report_not_json_native` JSON
- **AND** no Python traceback replaces the machine-readable result

#### Scenario: A notification needs no admission

- **WHEN** Git reports an irrelevant or completed notification
- **THEN** the hook does not initialize policy or CLI machinery for serialization
