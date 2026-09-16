## ADDED Requirements

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
