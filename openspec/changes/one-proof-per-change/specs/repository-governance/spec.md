## ADDED Requirements

### Requirement: An unlanded archive returns to its pre-archive head

Until its Work Lane lands, the Lease holder SHALL be able to compensate an
attested archive commit at the exact archived HEAD. One Lease-bound
compare-and-swap SHALL restore the archive commit's parent, and the index and
worktree SHALL then match that parent. Compensation SHALL be attested and SHALL
NOT create another intent, proof or archive authority.

#### Scenario: A failed archived-head proof returns

- **WHEN** the archived HEAD's proof fails and the holder compensates at that exact HEAD
- **THEN** the lane ref, index and worktree equal the pre-archive HEAD
- **AND** the active Change is available again for repair and a later archive
- **AND** the compensation is recorded as one attested Git effect

#### Scenario: An inexact or landed archive is refused

- **WHEN** the HEAD is not an attested archive of the named Change, is contained in the candidate branch, the worktree is dirty, the expected HEAD differs or another actor holds the Lease
- **THEN** compensation is refused before any ref, index or worktree effect

#### Scenario: An interrupted compensation completes

- **WHEN** the compensating ref update completed but the index and worktree still hold the archived tree
- **THEN** repeating the same compensation restores them without a second ref update

## MODIFIED Requirements

### Requirement: Archive completion requires exact postimage quality

Archive completion SHALL require native OpenSpec validity and the existing
applicable proof for the actual resulting HEAD. Archive SHALL NOT require a proof
of the pre-archive HEAD, and Git effect evidence SHALL NOT establish postimage
quality. Pending verification SHALL preserve and report the observed committed
effect without claiming completion.

#### Scenario: Native postimage finding before Git CAS

- **WHEN** official archive projection would leave a canonical spec invalid or
  with a blocking native finding
- **THEN** ETHOS validates that actual uncommitted postimage before creating a
  commit or updating the lane ref
- **AND** it compensates its own archive mutation and reports a source delta
  repair path only when the native finding maps to that changed spec; otherwise
  it requires further resolution instead of retrying the unchanged archive
- **AND** an already staged caller-owned archive remains visible as retained
  mutation, not a falsely absent effect or permission to discard its bytes
- **AND** a valid authored Purpose or corrected requirement remains able to
  archive through the normal postimage proof boundary

#### Scenario: Archive changes an input consumed by a repository check

- **WHEN** an archive commits a resulting HEAD that has no passing applicable proof
- **THEN** archive reports blocked pending verification with the actual HEAD
- **AND** its continuation selects that HEAD's existing proof command and repository root
- **AND** the reported native command comes from the committed archive artifact,
  retaining `skip_specs` rather than reading a now-absent active Change
- **AND** stale, failed or unrelated proof cannot make archive completion pass

#### Scenario: Exact postimage proof is available

- **WHEN** native OpenSpec validity and exact postimage proof both pass
- **THEN** archive completion passes using the original effect evidence
- **AND** replay neither repeats Git effects nor reruns checks

#### Scenario: Final task completion accompanies the official archive

- **GIVEN** the selected source HEAD has its separately admitted review evidence
- **WHEN** the staged official archive only advances the top-level OpenSpec task checkboxes from open to complete
- **THEN** archive admission preserves the unchanged task descriptions and other source artifacts
- **AND** it recognizes the completed postimage without requiring a new prearchive source commit and repeated review CI
- **AND** unchanged or partly open tasks, changed task prose, or another content edit remains blocked with an exact cause
- **AND** the checkbox does not replace postimage validation, proof, or evidence of the external review

### Requirement: Exact proof query selects intent without weakening evidence

A proof query SHALL select the requested official intent, or the intent bound
to an explicitly selected Attestation. When both are explicit, they SHALL agree. Applicable evidence SHALL retain exact
source, policy, integrity, freshness and authority checks. Distinct intents
SHALL remain distinct queries; conflicting evidence for the same query SHALL
not be resolved by choosing a convenient proof.

#### Scenario: Several intents have proofs at the same source

- **WHEN** two official Changes have current proofs for one exact commit
- **THEN** an invocation selects only its own intent's proof
- **AND** an exact Attestation selection overrides the environment choice
- **AND** an unproven selected intent cannot borrow the other proof
- **AND** malformed evidence and same-intent contradictions remain blocking

#### Scenario: Explicit archive cannot borrow another intent's proof

- **GIVEN** two official Changes share the exact source and only one has proof
- **WHEN** archive explicitly requests the unproven Change
- **THEN** only that Change is archived, and its archived HEAD requires its own proof
- **AND** the other Change's proof or environment selection neither satisfies nor alters that archive

#### Scenario: Explicit archive remains selected through post-observation

- **WHEN** archive runs with an unrelated or invalid environment selection
- **THEN** admission and post-observation consume the explicit Change
- **AND** unselected intent remains unchanged and replay observes the prior effect

#### Scenario: Explicit proof constraints must agree

- **WHEN** a query names an Attestation and a different or invalid Change
- **THEN** it rejects instead of ignoring either explicit constraint
- **AND** matching active or attested archived intent remains admissible

#### Scenario: Several completed archives retain separate proof identities

- **GIVEN** two distinct accepted intents have verified archive effects
- **WHEN** either is explicitly selected at a later shared source commit
- **THEN** its exact archived acceptance remains available for proof and planning
- **AND** both contributed requirements and product results remain intact
- **AND** absent, unreadable, invalid or unverified intent is not silently accepted

#### Scenario: Full proof shares one current intent observation with audit

- **WHEN** full proof resolves an explicit intent that differs from its ambient default
- **THEN** governance audit consumes that same resolved OpenSpec observation
- **AND** it retains independent adopter, commit and release policy checks
- **AND** a new invocation observes current inputs rather than cached permission

## REMOVED Requirements

### Requirement: Proof execution carrier is not proof authority

**Reason**: The carrier proved a pre-archive HEAD while an official archive was staged in the Work Lane. Archive no longer requires that proof: `ethos lane archive-change` commits the staged archive, and the archived HEAD is proved in the clean Work Lane.

**Migration**: Commit a staged archive with `ethos lane archive-change`, then prove the archived HEAD. `ethos prove` no longer accepts `--execution-root`.

### Requirement: Carrier proof preserves independent admission boundaries

**Reason**: It bound the retired execution carrier. Source and index correspondence during a proof remains with quality's "Exact commit proof binds observed execution source", and the current policy floor with "Current-policy proof coexists with immutable superseded proofs".

**Migration**: None. Ordinary proofs already run in the clean Work Lane.
