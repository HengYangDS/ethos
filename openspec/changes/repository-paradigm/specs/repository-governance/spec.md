## MODIFIED Requirements

### Requirement: Commit And Hosted Verification Policy

One owner SHALL compile commit policy for subject, signature and optional
author/committer constraints from the paradigm contract and the tracked
`[commit_policy]` declaration; every introduced commit carries an SSH signature.
Identity, cryptographic trust, transport and Forge attribution SHALL remain
distinct. Admission SHALL apply trusted prestate policy; a candidate SHALL NOT
waive its own integration obligations.

#### Scenario: Real signature verification

- **WHEN** admission evaluates an introduced commit
- **THEN** admission verifies exact object bytes against the protected trust anchor
- **AND** a signature envelope with invalid cryptography is rejected

#### Scenario: Verification inputs remain current

- **WHEN** one or many exact objects are verified against native SSH trust
- **THEN** every object uses the same captured configuration, anchor and revocation material
- **AND** source trust changes before observation completes reject the result
- **AND** temporary verification material is removed on normal exit or reported failure

#### Scenario: Identity requirements are declared

- **WHEN** policy constrains author or committer identity
- **THEN** the same constraint is checked before commit and on integrated objects
- **AND** absent constraints add no generic-adopter identity restriction

#### Scenario: Candidate weakens signing policy

- **WHEN** a candidate declares `signing_required = false` or another signing format
- **THEN** compilation ignores the restated field
- **AND** its introduced range still requires a trusted SSH signature on every commit

#### Scenario: Malformed policy fails closed

- **WHEN** a present identity constraint has malformed or unknown fields
- **THEN** compilation returns a precise error rather than disabling admission

#### Scenario: Independent evidence planes

- **WHEN** CI verifies an existing commit
- **THEN** it invokes the common owner without inventing authors or signing keys
- **AND** local signature success does not claim Forge verification

#### Scenario: Current commit policy is audited

- **WHEN** repository audit or head-bound proof evaluates current commit policy
- **THEN** it reports the compiled declaration, local identity, subject, and
  signature facts through the same compiler used by mutation
- **AND** it does not infer tracked policy from mutable Git configuration or
  GitLab verification from local Git output.

#### Scenario: Identity allowlist fields have no policy meaning

- **WHEN** a present commit-policy table contains `identity_mode` or
  `allowed_identities`
- **THEN** compilation fails closed with the exact unknown fields
- **AND** ETHOS does not preserve them as permissions, trust anchors, or
  compatibility metadata.

#### Scenario: CI verifies but does not manufacture commit identity

- **WHEN** a native CI projection prepares Git for repository checks
- **THEN** it does not synthesize an author identity, signing key, or
  `commit.gpgsign` setting when the job creates no commit
- **AND** it verifies existing objects through the repository-owned gates
  without an embedded TOML parser or policy default.

### Requirement: Refresh-base replay is signing-bound and compare-and-swap safe

ETHOS SHALL replay the admitted Work Lane SHA onto the admitted candidate SHA
through native Git rebase using the compiled commit policy and the paradigm's
SSH signature. It SHALL revalidate both admitted SHA snapshots immediately
before replay, validate every new replayed subject and signature before any
Git-common effect, and compare-and-swap the Work Lane ref from its admitted old
SHA before attaching it again.

#### Scenario: Ambient Git configuration attempts to disable tracked signing

- **GIVEN** a governed repository
- **AND** ambient or local Git configuration disables `commit.gpgsign`
- **WHEN** `ethos lane refresh-base --apply` replays one or more commits
- **THEN** every new replayed object is still SSH-signed
- **AND** every object passes the configured trust verifier before the Work Lane
  ref or Lease changes.

#### Scenario: unavailable signing transport blocks before replay

- **GIVEN** the repository's configured signer cannot create a replayed object
  non-interactively
- **WHEN** native rebase attempts to create its first replayed object
- **THEN** ETHOS reports the captured Git failure instead of a speculative
  signer-probe result
- **AND** it aborts replay and restores the original branch, HEAD, index,
  worktree, ref, and Lease.

#### Scenario: A replayed subject or signature is invalid

- **GIVEN** native rebase produced a candidate-descended detached HEAD
- **WHEN** any commit in the exact candidate-to-rebased range violates the
  compiled subject policy or fails signature trust
- **THEN** ETHOS reports the first exact policy or trust gap
- **AND** it restores the pre-refresh state before any Git-common effect.

#### Scenario: admitted snapshots move during preflight

- **GIVEN** a refresh captured Work Lane and candidate SHA values
- **WHEN** either value changes before replay, or the Work Lane ref changes
  before compare-and-swap
- **THEN** ETHOS reports the corresponding `refresh_base_snapshot_stale` gap
- **AND** it does not overwrite the newer ref or retain a replayed checkout.

#### Scenario: Work Lane moves before replay compare-and-swap

- **GIVEN** detached replay produced and validated a candidate-descended HEAD
- **WHEN** the Work Lane ref no longer equals its admitted old SHA before
  compare-and-swap
- **THEN** ETHOS reports `refresh_base_snapshot_stale:work_lane`
- **AND** it reattaches to the newer branch state without overwriting that ref.

### Requirement: Commit policy applies to exact introduced commit ranges

ETHOS SHALL compile the commit policy, the paradigm's subject grammar and SSH
signature with the optional tracked `.ethos/workspace.toml [commit_policy]`
declaration, through the existing repository-policy owner and apply that
compiled policy only to the commits newly introduced by one proposed Git ref
update. The range projection SHALL be provider-neutral, SHALL preserve the
repository object format, and SHALL NOT reinterpret or revalidate commits
already reachable from the trusted baseline.

#### Scenario: Existing ref receives a normal fast-forward

- **WHEN** a non-delete update supplies readable remote and proposed commit
  objects
- **THEN** ETHOS validates each commit reachable from the proposed commit but
  not from the remote commit in deterministic oldest-first order
- **AND** commits already reachable from the remote commit are not revalidated.

#### Scenario: Existing ref receives a non-fast-forward update

- **WHEN** the proposed commit does not descend from the readable remote commit
- **THEN** ETHOS still reports and validates exactly the commits newly reachable
  from the proposed commit
- **AND** the existing topology and ref-movement policy independently decides
  whether the non-fast-forward effect is admissible.

#### Scenario: A new proposal ref has a trusted accepted baseline

- **WHEN** the remote object ID is the repository-native zero object ID and the
  target has proposal role
- **THEN** ETHOS resolves the declared remote's accepted ref as the trusted
  baseline and validates only the proposed commits not reachable from it
- **AND** it blocks if that baseline is absent, unreadable, or not an ancestor of
  the proposed commit.

#### Scenario: A new non-proposal ref has no trustworthy baseline

- **WHEN** the remote object ID is zero and no exact trusted baseline is supplied
  or derivable for the target
- **THEN** ETHOS fails closed with a baseline gap
- **AND** it does not substitute the root commit or scan all repository history.

#### Scenario: An accepted or release object is projected to an absent ref

- **WHEN** an accepted branch, release branch, or annotated release tag has a
  zero remote object ID
- **AND** the exact proposed commit has one valid accepted-closeout Attestation
- **THEN** ETHOS uses that Attestation's accepted pre-state as the trusted
  historical baseline
- **AND** local publication dry-run and the real pre-push transport validate the
  same introduced revisions without trusting another remote or an unrelated
  sibling ref.

#### Scenario: A delete update is observed

- **WHEN** the proposed object ID is the repository-native zero object ID
- **THEN** commit-range admission reports a no-range delete result
- **AND** it leaves deletion authority to the existing ref policy.

#### Scenario: An annotated tag is proposed

- **WHEN** either endpoint names an annotated tag object
- **THEN** range admission peels that endpoint to its exact commit before
  deriving introduced commits
- **AND** tag-object trust remains governed by the existing publication owner.

#### Scenario: Commit policy is absent or malformed at the proposed tip

- **WHEN** the proposed committed tree contains no `[commit_policy]` table
- **THEN** ETHOS applies the paradigm's subject grammar and SSH signature to the
  introduced range
- **AND** when the table is present but malformed, admission fails closed before
  returning a passing range result.

### Requirement: Commit signature declaration and signer trust remain distinct

For commit-range admission, the paradigm's SSH signature SHALL govern the
presence and format of the signature embedded in each introduced commit.
Signer authorization and trust-anchor verification SHALL remain a separate
operation-specific observation and SHALL NOT require a repository-tracked key
list or provider-specific policy parser.

#### Scenario: A declared signature is missing or has the wrong format

- **WHEN** an introduced commit lacks a signature or carries a format other
  than SSH
- **THEN** the shared range validator reports the exact commit and signature gap
- **AND** local push admission and hosted CI reach the same verdict.

#### Scenario: A lifecycle operation creates or replays commits

- **WHEN** ETHOS itself creates or replays an object
- **THEN** it uses the same subject and signature-format validator
- **AND** its existing local trust verifier additionally proves the configured
  signer before any ref, Lease, or worktree effect is retained.

### Requirement: Structured documentation metadata preserves meaning

ETHOS SHALL preserve metadata identity, purpose, lifecycle and typed relationships
under valid syntax variations. Invalid declarations and unresolved required
authority targets SHALL be reported. Human-readable and machine-readable
representations SHALL agree on the same declared meaning.

#### Scenario: Equivalent and ambiguous metadata are distinguished

- **WHEN** metadata uses valid quoted scalars or structured relationships
- **THEN** public observation preserves the equivalent meaning
- **AND** duplicate keys and unclosed frontmatter cannot silently pass

#### Scenario: Required guidance is absent or contradictory

- **WHEN** a required authority target is missing or visible state contradicts metadata
- **THEN** public observation identifies the exact disagreement or missing target
- **AND** literal examples cannot satisfy actual reader-guidance obligations

#### Scenario: A selected documentation source disappears during observation

- **WHEN** a document selected by the registry becomes missing or unreadable before downstream checks finish
- **THEN** the public docs report identifies the unavailable source and blocks
- **AND** an earlier metadata observation cannot turn that incomplete read into a pass

#### Scenario: Selected documentation renders its title before metadata

- **WHEN** a profile-selected Markdown document encloses its leading YAML metadata in an HTML comment
- **THEN** the registry reads no metadata from it and reports the document's metadata as missing
- **AND** the repository paradigm names the comment wrapper to remove, so plain front matter is the only carrier

#### Scenario: Adopter-native guidance satisfies a portable reader floor

- **WHEN** an active profile-selected page has a visible H1 and non-empty non-heading text outside code fences, but not ETHOS-specific `Status`, `Purpose`, or `See also` labels
- **THEN** the docs report accepts its reader surface if metadata, relations, and navigation are valid
- **AND** a missing title or guidance hidden entirely in a literal fence blocks
- **AND** an authored empty or contradictory `Status:` remains a gap
- **AND** observational roles may omit reader guidance

## REMOVED Requirements

### Requirement: Predecessor branch-role tables keep their incumbent meaning

**Reason**: The repository paradigm fixes every branch role name, and `.ethos/release.toml` declares the release mirror, so ETHOS reads no `[branch_roles]` table and no predecessor table generation needs a compatibility reading.

**Migration**: Accepted closeout renames legacy role refs to the standard names; the legacy declarations are then removed from `.ethos/workspace.toml`.
