## ADDED Requirements

### Requirement: Independent release selection preserves accepted source

ETHOS SHALL expose proof-bound promotion of exact current accepted source to the
declared independent release ref through existing land and Git effect owners.
Fresh source and prior release coordinates, accepted effect, repository-transition
proof and local coordination SHALL remain independent preconditions.

#### Scenario: Accepted source is selected for release

- **WHEN** an authorized request names current accepted and prior release objects
- **THEN** one native CAS advances release without rewriting source
- **AND** the transaction asserts the accepted ref
- **AND** dirty linked release content causes rejection before the effect

#### Scenario: Release movement lacks authority

- **WHEN** source differs from accepted or proof, accepted effect or executor
  intent is missing or stale
- **THEN** release admission rejects without a partial ref update

### Requirement: Release tags preserve native product version authority

ETHOS SHALL create requested signed annotated release tags from exact committed
native version authority through the existing Git effect. Missing, malformed or
conflicting version inputs SHALL block. A product with a native package version
SHALL NOT require a parallel VERSION carrier.

#### Scenario: Native package version owns release

- **WHEN** package.json is the unambiguous committed version owner
- **THEN** the tag matches that version and peels to accepted
- **AND** its signature passes current protected trust verification
- **AND** release and new tag refs update in one native transaction

#### Scenario: Tag or version conflicts

- **WHEN** the requested tag disagrees with version, is already divergent, or
  lacks a trusted signature
- **THEN** neither release nor tag ref changes

#### Scenario: Interrupted or repeated release

- **WHEN** release resumes after an observed or unknown effect
- **THEN** ETHOS observes exact refs and evidence before replay
- **AND** an accepted tag object is reused without resigning
- **AND** pending linked worktree synchronization remains explicit

### Requirement: Accepted delivery is not another contribution integration

ETHOS SHALL distinguish shipping exact verified accepted content from introducing
new contributions. Only the former may reuse accepted effect and current proof.
Reuse SHALL NOT assert signatures or later-policy compliance for pre-adoption
history.

#### Scenario: Accepted source contains pre-adoption history

- **WHEN** accepted source with valid effect and proof is selected for main or tag
- **THEN** publication preserves history without rescanning accepted ancestors as
  new contributions
- **AND** exact source, tag signature, target policy and peer CAS remain required

#### Scenario: Content was not accepted

- **WHEN** proposed source differs from current accepted or its evidence fails
- **THEN** reuse grants no admission
- **AND** normal introduced-range subject and signature checks remain enforced
