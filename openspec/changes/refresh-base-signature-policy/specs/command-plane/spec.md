## MODIFIED Requirements

### Requirement: Lifecycle commit objects inherit repository signing policy

ETHOS SHALL create direct lifecycle commit objects through one owner that
compiles the optional tracked `[commit_policy]` declaration from
`.ethos/workspace.toml`, validates the explicit commit subject, projects any
required signing configuration into Git execution, and verifies the resulting
object before a ref, Lease, or worktree effect.

#### Scenario: Signing is enabled and trusted

- **GIVEN** the tracked commit policy requires signing
- **WHEN** a lifecycle operation creates a commit object
- **THEN** the Git invocation requires the declared signing format even when
  ambient or local `commit.gpgsign` is absent or false
- **AND** external trust verification passes before any repository effect.

#### Scenario: Signing is disabled

- **WHEN** a repository has no `[commit_policy]` declaration or its tracked
  policy does not require signing
- **THEN** ETHOS adds no repository-independent subject or signing constraint
- **AND** mutable Git configuration does not become an implicit ETHOS policy.

#### Scenario: Tracked commit policy is malformed

- **WHEN** a present commit-policy table has an unknown field, invalid type,
  invalid subject expression, or unsupported signing format
- **THEN** the lifecycle operation reports the exact policy gap before invoking
  a mutating Git command
- **AND** it does not fall back to ambient Git policy.

#### Scenario: Generated subject is not admitted

- **WHEN** an ETHOS lifecycle operation proposes or receives a subject that does
  not match the tracked `subject_pattern`
- **THEN** the operation blocks before object creation and exposes one explicit
  subject input as its continuation
- **AND** ETHOS does not emit a hard-coded universal replacement subject.

#### Scenario: Required signature is not trusted

- **WHEN** object creation, signing, or external trust verification fails under
  a tracked signing requirement
- **THEN** the lifecycle operation reports the typed signing gap with the Git
  execution diagnostics
- **AND** no ref, Lease, or worktree effect remains.
