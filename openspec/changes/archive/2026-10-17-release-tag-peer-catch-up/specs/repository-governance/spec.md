## MODIFIED Requirements

### Requirement: Accepted delivery is not another contribution integration

ETHOS SHALL distinguish shipping exact verified accepted content from introducing
new contributions. Only the former may reuse accepted effect and current proof.
Reuse SHALL NOT assert signatures or later-policy compliance for pre-adoption
history. Accepted content is the current accepted commit or, for an existing
release tag object, the commit at which an attested ETHOS release effect
created that object while that commit remains in accepted history.

#### Scenario: Accepted source contains pre-adoption history

- **WHEN** accepted source with valid effect and proof is selected for main or tag
- **THEN** publication preserves history without rescanning accepted ancestors as
  new contributions
- **AND** exact source, tag signature, target policy and peer CAS remain required

#### Scenario: Content was not accepted

- **WHEN** proposed source is neither current accepted nor the attested release
  commit of the exact tag object in accepted history, or its evidence fails
- **THEN** reuse grants no admission
- **AND** normal introduced-range subject and signature checks remain enforced

### Requirement: Native pre-push validates release-tag objects

ETHOS native pre-push SHALL validate the actual object supplied for a declared
release-tag ref as a trusted signed annotated tag with exact declared name and
committed product version at its release commit: the current accepted commit,
or an earlier accepted commit where an attested release effect created exactly
this tag object. A signed peeled commit alone SHALL NOT satisfy tag admission.
A divergent remote tag SHALL NOT be replaced, and exact remote publication
SHALL reach the same decision.

#### Scenario: Plain commit is offered as a release tag

- **WHEN** Git supplies a commit OID as the new value of a declared
  `refs/tags/vX.Y.Z` update
- **THEN** native pre-push exits nonzero with a tag-object gap
- **AND THEN** passing commit proof does not authorize the update.

#### Scenario: Signed tag is published or already current

- **WHEN** Git supplies a trusted signed annotated tag matching the exact ref
  name, committed version and current accepted commit
- **THEN** native pre-push can admit creation while the remote tag is absent,
  or an identical remote no-op
- **AND THEN** it retains current proof, accepted effect and ref-role checks.

#### Scenario: A peer that missed the release receives it later

- **WHEN** accepted history has advanced past a release commit and a declared
  peer lacks the exact tag object the attested release effect created there
- **THEN** native pre-push and exact publication can admit that object for the
  selected peer, or an identical remote no-op
- **AND THEN** tag trust, name, version, proof and accepted effect are checked
  for the release commit and the publication effect is attested.

#### Scenario: Tag object or remote state is invalid

- **WHEN** the tag is lightweight, unsigned, untrusted, mismatched by name or
  version, neither at the current accepted commit nor the attested object of a
  release still in accepted history, or replaces a different remote tag object
- **THEN** native pre-push blocks without a remote effect.
