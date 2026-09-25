## MODIFIED Requirements

### Requirement: Publication composes historical repair with forward integration

ETHOS SHALL recognize a completed exact historical repair followed by native
ancestor-related commits when a selected protected peer ref holds either the
recorded former tip or an earlier original commit explicitly mapped by that
repair. The target ref SHALL be included in the repair's exact ref effect. The
common range owner SHALL validate only commits after the verified replacement
tip under its baseline and proposed policies. Proposed-object proof, current
accepted effect, candidate equality, tag-object admission and remote CAS remain
independent requirements.

#### Scenario: Signed forward commits follow a verified replacement

- **WHEN** the peer ref holds the recorded repair source and proposed accepted
  descends from its verified replacement
- **THEN** publication recognizes the historical segment as repaired
- **AND THEN** the common range owner checks replacement-to-proposed commits
  without scanning the repaired historical segment as new integration.

#### Scenario: Peer holds an earlier mapped original commit

- **WHEN** the protected peer ref holds an exact original commit in the
  completed repair mapping and the repair replaced that same local ref
- **THEN** pre-push and publication readiness use the verified replacement
  tip as the forward-validation baseline
- **AND THEN** the peer's advertised old OID remains the exact CAS precondition
  rather than being substituted with the mapped or replacement OID.

#### Scenario: A forward commit violates policy

- **WHEN** a descendant after the verified replacement has an invalid subject,
  identity or required signature
- **THEN** range admission rejects that descendant despite valid repair
  provenance.

#### Scenario: Repair provenance does not establish the requested relationship

- **WHEN** the target ref is not in the repair, the peer's old OID is not a
  mapping key, replacement ancestry is absent, or repair evidence is missing,
  invalid or ambiguous
- **THEN** the request is not admitted as a repaired-history publication
- **AND THEN** no remote or local ref is changed by the observation.

#### Scenario: Accepted publication consumes the verified forward baseline

- **WHEN** public pre-push or publication evaluates accepted descendants after
  a verified repair of the peer's exact old object or mapped historical prefix
- **THEN** the accepted topology check evaluates forward ancestry from the
  verified replacement while still requiring the current candidate head
- **AND THEN** proposed-object proof and its accepted effect remain required
- **AND THEN** each peer applies only its observed old-to-proposed ref
  transaction.

#### Scenario: Repaired ancestry cannot excuse missing current acceptance

- **WHEN** the repair relation is valid but current proof, accepted effect or
  candidate equality is absent
- **THEN** publication is rejected without changing either peer.

## ADDED Requirements

### Requirement: Native pre-push validates release-tag objects

ETHOS native pre-push SHALL validate the actual object supplied for a declared
release-tag ref as a trusted signed annotated tag with exact declared name,
committed product version and current accepted source. A signed peeled commit
alone SHALL NOT satisfy tag admission. The remote tag MAY be absent or already
point to the identical tag object; a divergent remote tag SHALL NOT be replaced.

#### Scenario: Plain commit is offered as a release tag

- **WHEN** Git supplies a commit OID as the new value of a declared
  `refs/tags/vX.Y.Z` update
- **THEN** native pre-push exits nonzero with a tag-object gap
- **AND THEN** passing commit proof does not authorize the update.

#### Scenario: Signed tag is published or already current

- **WHEN** Git supplies a trusted signed annotated tag matching the exact ref
  name, committed version and current accepted commit
- **THEN** native pre-push can admit creation or an identical remote no-op
- **AND THEN** it retains current proof, accepted effect and ref-role checks.

#### Scenario: Tag object or remote state is invalid

- **WHEN** the tag is lightweight, unsigned, untrusted, mismatched by name or
  version, detached from current accepted source, or replaces a different
  remote tag object
- **THEN** native pre-push blocks without a remote effect.
