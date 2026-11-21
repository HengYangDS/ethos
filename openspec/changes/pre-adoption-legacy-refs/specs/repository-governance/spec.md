# repository-governance delta

## MODIFIED Requirements

### Requirement: Historical effect identity survives profile schema evolution

ETHOS SHALL validate repair and Git-ref-effect Attestations, and the accepted
pre-state revisions of a current Git effect, including the unedited accepted
checkout a closeout advances, against each exact former commit's stable
repository identity, not today's schema. Missing, malformed or mismatched
historical identity SHALL block without current-profile or caller fallback.

#### Scenario: Retired profile field does not erase a valid repair

- **GIVEN** a completed exact repair of a former accepted commit whose profile
  declares the same repository ID and a field removed from the current schema
- **WHEN** publication checks a declared peer still holding an original commit
  covered by that repair
- **THEN** provenance validation uses the former commit's stable identity
- **AND THEN** the old field alone does not block the repaired-history relation
- **AND THEN** current proof, target policy and remote CAS remain independent
  conditions before any effect.

#### Scenario: Accepted closeout remains verifiable after profile cleanup

- **GIVEN** a completed candidate-to-accepted effect whose former commit has
  the same repository ID but a field later removed from the profile schema
- **WHEN** publication revalidates the accepted effect at the new source HEAD
- **THEN** its recorded Git effect remains verifiable against the former
  commit's stable repository identity
- **AND THEN** it does not report the accepted closeout as unattested solely
  because the former profile has an obsolete field.

#### Scenario: An adopter lands its profile migration across a retired schema

- **GIVEN** an adopter whose accepted candidate head and unedited accepted
  checkout declare the same repository ID with formats removed from the current
  profile schema
- **WHEN** its Work Lane lands a candidate that migrates the profile to the
  current schema and closeout advances the accepted checkout to it
- **THEN** each Git effect reads that accepted pre-state through its stable
  historical identity
- **AND THEN** control replacement keeps the predecessor's committed
  verification mode, requires it when unreadable, and binds the exact candidate
- **AND THEN** the produced candidate revision is validated against the current
  schema
- **AND THEN** an edited accepted checkout, a changed repository ID, an invalid
  produced profile and the trust, ref role, CAS, proof and lease refusals still
  block.

#### Scenario: Historical identity cannot be guessed

- **WHEN** the former profile is unreadable, syntactically malformed, declares
  no nonempty repository ID, or declares a different repository ID, or it is
  absent while a commit in the revision's history carries a profile or the
  accepted head does not descend from the revision
- **THEN** historical repair or effect provenance is rejected before publication
- **AND THEN** the current profile, receipt text or peer name does not replace
  the former commit's identity.

#### Scenario: Other repair bindings remain mandatory

- **WHEN** the historical identity matches but the recorded policy or commit
  payload digest, signed replacement relation, effect Attestation or current
  source proof is invalid
- **THEN** the corresponding existing admission blocks publication
- **AND THEN** no peer ref changes.

#### Scenario: Current profile remains strict

- **WHEN** the current checkout's profile violates the current typed schema
- **THEN** status, planning, proof and publication remain blocked
- **AND THEN** historical identity tolerance cannot validate the current
  operational profile.

### Requirement: Absorbed-ref retirement previews agree with the prepared hook

An absorbed-ref retirement preview SHALL evaluate the reference-transaction
hook's legacy role protection and ref-move policy resolution through the hook's
own predicates, without claiming the retirement's intent. A deletion that the
hook would refuse for either reason SHALL block the preview with the hook's gap,
and the preview SHALL NOT emit an apply command for it. A lane abandonment SHALL
ask the same predicate before it persists an operation and before its apply
removes anything.

#### Scenario: A protected legacy role ref

- **WHEN** an absorbed-ref retirement selects a ref that the accepted head's committed table
  declares as a legacy role name, and no successor ref holds its commit
- **THEN** the preview blocks with `legacy_role_ref_protected` and names the accepted closeout
- **AND** it emits no apply command.

#### Scenario: No strict policy governs the deletion

- **WHEN** neither the deleted commit nor the accepted head carries a release binding or a valid
  profile, or the accepted head carries a release binding that cannot be honored
- **THEN** the preview blocks with `ref_move_policy_unavailable`
- **AND** it emits no apply command.

#### Scenario: An abandonment the hook would refuse

- **WHEN** a lane abandonment selects a ref whose deletion the hook would refuse
- **THEN** its derivation blocks with the hook's gap before any worktree is removed
- **AND** it persists no operation.

#### Scenario: A receipt whose deletion now refuses

- **WHEN** an abandonment's persisted operation is applied after the hook's
  answer for its ref deletion has changed to a refusal
- **THEN** the apply blocks with the hook's gap
- **AND** it removes no worktree and deletes no ref.

#### Scenario: A legacy release ref before its rename

- **WHEN** an absorbed-ref retirement selects the legacy release ref that the
  accepted head's committed table names, at a commit that holds no table
- **THEN** the preview blocks with `legacy_role_ref_protected` and names the
  accepted closeout
- **AND** a root that has an older commit checked out gets the same answer
- **AND** a table that cannot be read takes nothing from the other table's answer.

## ADDED Requirements

### Requirement: A pre-adoption pre-state is read under the accepted identity

A pre-state revision in whose complete history no commit carries the repository
profile, and from which the accepted branch's head descends, SHALL be read under
the accepted head's identity, which SHALL agree with every other revision of the
effect. Current effects SHALL still require the strict current profile in every
other checkout and every revision they produce; a ref that an effect creates at
the commit the same effect deletes produces no revision.

#### Scenario: A pre-state that predates the adoption

- **GIVEN** a legacy release ref at a commit in whose history no commit carries
  `.ethos/profile.toml`, and an accepted head that descends from it
- **WHEN** an accepted closeout renames that ref, a later closeout fast-forwards
  the release mirror from it, or a release names it as the previous release head
- **THEN** its pre-state is read under the accepted head's identity
- **AND THEN** the same commit after a later deletion of its profile, a commit
  that the accepted head does not descend from, or a history too shallow to show
  that it never carried a profile, still blocks.

#### Scenario: A rename creates no revision

- **WHEN** a legacy role ref stands at a commit that carries no profile, or one
  whose profile carries a field removed from the current schema
- **THEN** closeout renames it, and the standard ref it creates at that commit
  is not read under the current schema
- **AND** an effect that moves another ref onto that commit still reads it
  under the current schema and blocks.
