## MODIFIED Requirements

### Requirement: Git commit-message admission validates the final subject

The package runtime SHALL execute a `commit-msg` hook that reads the final
message file and compiles commit policy from the prospective index tree. It SHALL
validate the first message line against the commit grammar, and the whole message
above Git's scissors line against the paradigm's private-address pattern, before
Git creates the commit. It SHALL NOT claim that a not-yet-created object has a
valid signature.

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

#### Scenario: A verbose commit removes a private address

- **WHEN** `git commit --verbose` places a staged diff that removes a
  private-class address below the scissors line
- **THEN** `commit-msg` admits a message whose text above that line names no such
  address.
