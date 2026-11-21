# repository-paradigm delta

## MODIFIED Requirements

### Requirement: Accepted closeout renames legacy role refs

When the committed table declares a legacy name for the accepted, candidate or release role,
accepted closeout SHALL, in one ref transaction, create each standard role ref at the head of the
legacy ref it replaces and delete that legacy ref, and SHALL bind each worktree on a renamed ref
by compare-and-swap in an authorized apply, on Git 2.46 or later. Git
admission SHALL refuse any other move of a legacy role ref, except deleting one whose successor
holds its commit.

#### Scenario: A repository adopted under legacy names

- **WHEN** the committed table names `accepted/train` and `candidate/train` and the accepted root
  is bound to `accepted/train`
- **THEN** closeout leaves `dev` and `candidate/dev` at the heads those refs had and removes the
  legacy refs
- **AND** the accepted and candidate worktrees are bound to `dev` and `candidate/dev`.

#### Scenario: A legacy role ref is moved directly

- **WHEN** a user runs `git branch -m accepted/train dev`
- **THEN** Git admission refuses the update with `legacy_role_ref_protected`.

#### Scenario: A legacy role ref duplicates its successor

- **WHEN** the committed table names `integration/dev` as the legacy candidate name, and
  `candidate/dev` holds the same commit as `integration/dev`
- **THEN** the absorbed-ref retirement deletes `integration/dev`, and Git admission admits that
  deletion
- **AND** no other legacy role ref is renamed or moved.

#### Scenario: An interrupted binding is previewed

- **WHEN** the refs are renamed but the accepted and candidate worktrees still name `accepted/train`
  and `candidate/train`
- **THEN** `ethos land --closeout --json` reports `branch_role_rebinding_pending` for both and
  changes no `HEAD`
- **AND** its next action is the closeout apply with `--expect-head` set to the head of `dev`

#### Scenario: A refused apply binds nothing

- **WHEN** that apply lacks `--authorize` or names another head
- **THEN** it blocks and every `HEAD` still names its legacy ref

#### Scenario: A worktree moves after detection

- **WHEN** a worktree's `HEAD` no longer names its legacy ref when the binder writes
- **THEN** that worktree keeps its `HEAD` and the apply blocks with
  `branch_role_worktree_binding_stale`

#### Scenario: Git lacks symbolic-ref transactions

- **WHEN** Git refuses the `symref-verify` probe of `git update-ref --stdin`
- **THEN** the rename, retained-topic and rebinding applies refuse with
  `branch_role_rename_git_unsupported` and no ref or `HEAD` moves

#### Scenario: Only the release name is legacy

- **WHEN** the committed table names `master` as the release branch and the
  standard names for every other role, and the accepted root is bound to `dev`
- **THEN** closeout renames `master` to `main` and moves no other ref.

## ADDED Requirements

### Requirement: An unrelated legacy role ref is never renamed

Git admission SHALL NOT rename a legacy role ref whose history carries no repository profile
and that the accepted head does not descend from; the refusal names the branch.

#### Scenario: A legacy role ref without shared history

- **WHEN** the committed table names `master` as the release branch, no commit in
  `master`'s history carries a profile, and the accepted head does not descend
  from `master`
- **THEN** closeout blocks with `legacy_role_rename_history_unshared:master`
- **AND** no ref moves.
