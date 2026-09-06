## ADDED Requirements

### Requirement: Commit policy has one executable admission surface

ETHOS SHALL expose one JSON-composable commit-range admission command under the
existing hook command namespace. The command SHALL accept explicit named target,
proposed-head, remote-head, remote, and optional trusted-baseline coordinates and
SHALL return the exact range, policy projection, checked commit count, violations,
stable gaps, and one next action without performing a mutation.

#### Scenario: A local or hosted transport requests range admission

- **WHEN** `ethos hook commit-range` receives complete readable coordinates
- **THEN** it invokes the same repository range and commit-policy owner used by
  pre-push
- **AND** its JSON verdict is independent of GitHub, GitLab, or shell syntax.

#### Scenario: Coordinates are stale or incomplete

- **WHEN** an endpoint, baseline, committed policy, or introduced range cannot
  be read exactly
- **THEN** the command fails closed with the failing coordinate and stable gap
- **AND** it does not infer a replacement revision or inspect all history.

### Requirement: Git commit-message admission validates the final subject

The package runtime SHALL execute a `commit-msg` hook that reads the final
message file and compiles commit policy from the prospective index tree. It SHALL
validate only the first message line before Git creates the commit and SHALL NOT
claim that a not-yet-created object has a valid signature.

#### Scenario: Raw Git commit has an invalid subject

- **WHEN** a repository with a valid commit policy invokes ordinary `git commit`
  with a non-conforming final subject
- **THEN** the installed `commit-msg` transport rejects object creation with
  `commit_subject_invalid`
- **AND** it uses no parser or grammar other than the existing `CommitPolicy`.

#### Scenario: The staged policy changes in the same commit

- **WHEN** `.ethos/workspace.toml` is added, changed, or removed in the index
- **THEN** `commit-msg` evaluates the exact policy represented by that index
- **AND** unstaged working-tree bytes do not govern the prospective commit.

#### Scenario: Local commit-message transport is bypassed

- **WHEN** a commit is created with `git commit --no-verify`
- **THEN** no local pre-object claim is made
- **AND** pre-push and hosted commit-range admission still validate the created
  object through the same policy owner.

### Requirement: Commit-policy enforcement capability is discoverable

Repository status SHALL report whether the optional policy is declared and
whether the installed `commit-msg` and `pre-push` transports are exact current
launchers for the selected immutable runtime.

#### Scenario: Required transport is missing or stale

- **WHEN** a declared policy exists but either launcher is absent, modified, or
  bound to a stale runtime generation
- **THEN** status identifies the unavailable enforcement boundary
- **AND** it returns the existing exact `ethos hook install --root <root> --json`
  repair command rather than asking the adopter to inspect source.

#### Scenario: Policy is not declared

- **WHEN** the repository has no `[commit_policy]` declaration
- **THEN** status reports the capability as not declared without adding a gap
- **AND** hook installation remains valid for the repository's other controls.
