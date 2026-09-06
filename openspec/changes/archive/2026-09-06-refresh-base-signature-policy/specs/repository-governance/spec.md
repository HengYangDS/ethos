## MODIFIED Requirements

### Requirement: Commit And Hosted Verification Policy

ETHOS SHALL compile repository commit policy from the optional tracked
`.ethos/workspace.toml [commit_policy]` table through one repository-policy
owner. Repository audit, lifecycle mutation, and Git execution SHALL consume
that compiled value. The tracked table SHALL contain only subject syntax,
signature requirement, and signing format. Local author and committer identity,
object signature trust, transport authentication, and forge-side verification
remain separate observations and SHALL NOT imply one another.

#### Scenario: Current commit policy is audited

- **WHEN** repository audit or head-bound proof evaluates current commit policy
- **THEN** it reports the tracked declaration, local identity, subject, and
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
through native Git rebase using the compiled tracked commit policy. It SHALL
revalidate both admitted SHA snapshots immediately before replay, validate every
new replayed subject and required signature before any Git-common effect, and
compare-and-swap the Work Lane ref from its admitted old SHA before attaching it
again.

#### Scenario: Ambient Git configuration attempts to disable tracked signing

- **GIVEN** the tracked commit policy requires signing
- **AND** ambient or local Git configuration disables `commit.gpgsign`
- **WHEN** `ethos lane refresh-base --apply` replays one or more commits
- **THEN** every new replayed object is still signed through the declared format
- **AND** every object passes the configured trust verifier before the Work Lane
  ref or Lease changes.

#### Scenario: unavailable signing transport blocks before replay

- **GIVEN** the tracked commit policy requires signing but its configured signer
  cannot create a replayed object non-interactively
- **WHEN** native rebase attempts to create its first replayed object
- **THEN** ETHOS reports the captured Git failure instead of a speculative
  signer-probe result
- **AND** it aborts replay and restores the original branch, HEAD, index,
  worktree, ref, and Lease.

#### Scenario: A replayed subject or signature is invalid

- **GIVEN** native rebase produced a candidate-descended detached HEAD
- **WHEN** any commit in the exact candidate-to-rebased range violates the
  tracked subject policy or fails required signature trust
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
