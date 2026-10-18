## MODIFIED Requirements

### Requirement: Current repository decisions have one resolution owner

ETHOS SHALL resolve role, actor, Lease, fresh Git facts, official intent, first
gap and recovery once per operation. Status/plan/prewrite/hooks/prove/archive
SHALL consume that typed authority, gap, next action and Commitment unchanged.
Non-pass SHALL stop downstream work; pass alone authorizes plan compilation.
Effects MAY recheck exact CAS or issuance preconditions, SHALL observe results,
and SHALL NOT reselect intent.

#### Scenario: One missing fact is observed by several surfaces

- **WHEN** status, plan, prewrite, a hook, and prove evaluate the same current repository state
- **THEN** they report the same first machine gap and the same recovery command
- **AND** no surface replaces it with adoption advice, a placeholder, or command-local prose

#### Scenario: A failed current resolution closes downstream planning

- **GIVEN** the shared current resolver returns a non-passing verdict, ordered gaps, one recovery action, and a user-decision fact
- **WHEN** a public operation consumes that resolution
- **THEN** it projects those fields unchanged and terminates before invoking its operation-specific planner, gate runner, or effect
- **AND** a command-local exception mapper cannot replace the failed resolution

#### Scenario: A valid Work Lane has current authority

- **WHEN** the invocation actor owns the lane's valid four-field Lease and the official active Change is resolvable
- **THEN** every consuming surface receives the same passing authority and fresh Git facts
- **AND** no historical carrier, transition Attestation, or command-local binding grants additional authority

#### Scenario: Archive planning reuses the selected intent

- **GIVEN** one archive invocation resolves a completed official Change and its Commitment
- **WHEN** archive readiness and the exact Git-effect plan are compiled
- **THEN** both consume that same current resolution
- **AND** neither rereads OpenSpec governance nor reloads Commitment

#### Scenario: Interrupted archive finalization preserves source identity

- **GIVEN** the worktree contains an exact staged official archive post-image while HEAD still contains the active Change
- **WHEN** the archive operation is resumed
- **THEN** the current resolver compiles intent once from that exact source HEAD
- **AND** the effect plan binds the same Commitment before applying exact CAS

#### Scenario: Archive post-observation does not reselect intent

- **WHEN** the admitted archive Git effect completes
- **THEN** ETHOS re-observes the resulting OpenSpec lifecycle to verify the postcondition
- **AND** that post-observation cannot replace the Commitment already bound into the plan

#### Scenario: Passing resolution freezes plan compilation

- **GIVEN** the shared current resolver returns a passing result
- **WHEN** an operation compiles its deterministic TransitionPlan
- **THEN** the planner consumes the authority, Lease generation, Commitment, scope, and Git facts from that resolution
- **AND** the planner does not reread those mutable inputs or perform a second authority decision

#### Scenario: Repository proof without active intent remains explicit

- **GIVEN** a candidate or accepted root has no active Change and no applicable archive Attestation
- **WHEN** ETHOS resolves current proof input without an explicit Change request
- **THEN** the shared resolver returns a passing repository resolution with no Commitment
- **AND** proof planning consumes that explicit result rather than ignoring an intent-resolution failure

#### Scenario: Attestation issuance rechecks mutable preconditions

- **GIVEN** a plan compiled from one passing frozen resolution
- **WHEN** ETHOS is about to issue the proof Attestation
- **THEN** the issuance owner re-observes exact HEAD, tree, repository identity, Lease generation, and invocation actor
- **AND** it rejects drift without recompiling the plan or selecting different intent

#### Scenario: Work Lane migration uses current policy

- **GIVEN** a Work Lane was created under a historical governance declaration
- **WHEN** ETHOS refreshes it onto an exact current candidate commit
- **THEN** commit grammar and signing policy are compiled from that candidate commit
- **AND** historical policy fields cannot block or authorize the migration
- **AND** branch-role observation ignores retired transition material that it does not own
- **AND** strict ref-mutation admission validates the declared branch-role settings exactly, while the paradigm fixes the role names

### Requirement: Commit-policy enforcement capability is discoverable

Repository status SHALL report whether the installed `commit-msg` and
`pre-push` transports are exact current launchers for the selected immutable
runtime and whether the commit trust anchor is configured.

#### Scenario: Required transport is missing or stale

- **WHEN** either launcher is absent, modified, or bound to a stale runtime
  generation
- **THEN** status identifies the unavailable enforcement boundary
- **AND** it returns the existing exact `ethos hook install --root <root> --json`
  repair command rather than asking the adopter to inspect source.

#### Scenario: A new transport exists only in an unaccepted Change

- **WHEN** the selected immutable runtime exactly matches accepted Git truth but
  the invoking Work Lane contains a newer commit-policy execution capability
- **THEN** status keeps the accepted runtime current and reports the newer
  capability as `pending_acceptance`
- **AND** it does not instruct the older accepted runtime to install a launcher
  or command that package does not contain.

#### Scenario: Accepted source requires a newer runtime

- **WHEN** accepted Git truth advances to source whose commit-policy execution
  capability is newer than the selected immutable runtime
- **THEN** status reports the selected runtime stale
- **AND** its repair action invokes the new accepted package rather than asking
  the superseded runtime to manufacture unknown semantics.

#### Scenario: Policy is not declared

- **WHEN** a governed repository has no `[commit_policy]` declaration
- **THEN** status still requires both launchers and a configured commit trust
  anchor, because the paradigm's commit policy applies
- **AND** a repository that ETHOS does not govern reports the capability as not
  governed without adding a gap.

## REMOVED Requirements

### Requirement: Lifecycle commit objects inherit repository signing policy

**Reason**: The repository paradigm requires an SSH signature on every commit, so no tracked declaration enables or disables signing and a repository without `[commit_policy]` no longer escapes the subject grammar or the signature.

**Migration**: Configure SSH signing and the commit trust anchor in every governed repository, then let `ethos lane repair-paradigm --apply` delete the restated `signing_required` and `signing_format` fields.

## ADDED Requirements

### Requirement: Lifecycle commit objects carry the paradigm's SSH signature

ETHOS SHALL create direct lifecycle commit objects through one owner that
compiles the repository commit policy, the paradigm's subject grammar and SSH
signature with the optional tracked `[commit_policy]` declaration from
`.ethos/workspace.toml`, validates the explicit commit subject, projects the
signing configuration into Git execution, and verifies the resulting object
before a ref, Lease, or worktree effect.

#### Scenario: Signing is enabled and trusted

- **GIVEN** a governed repository, with or without a tracked commit policy
- **WHEN** a lifecycle operation creates a commit object
- **THEN** the Git invocation requires an SSH signature even when ambient or local `commit.gpgsign` is absent or false
- **AND** external trust verification passes before any repository effect.

#### Scenario: A repository declares no commit policy

- **WHEN** a repository has no `[commit_policy]` declaration
- **THEN** ETHOS applies the paradigm's subject grammar and SSH signature
- **AND** mutable Git configuration does not become an implicit ETHOS policy.

#### Scenario: Tracked commit policy is malformed

- **WHEN** a present commit-policy table has an unknown field, invalid type, or invalid subject expression
- **THEN** the lifecycle operation reports the exact policy gap before invoking a mutating Git command
- **AND** it does not fall back to ambient Git policy.

#### Scenario: Generated subject is not admitted

- **WHEN** an ETHOS lifecycle operation proposes or receives a subject that the compiled grammar does not admit
- **THEN** the operation blocks before object creation and exposes one explicit subject input as its continuation
- **AND** ETHOS does not emit a hard-coded universal replacement subject.

#### Scenario: Required signature is not trusted

- **WHEN** object creation, signing, or external trust verification fails
- **THEN** the lifecycle operation reports the typed signing gap with the Git execution diagnostics
- **AND** no ref, Lease, or worktree effect remains.
