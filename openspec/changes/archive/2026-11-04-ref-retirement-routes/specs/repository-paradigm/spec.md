## MODIFIED Requirements

### Requirement: Accepted closeout renames legacy role refs

When the accepted root is bound to a ref that its committed table declares as a legacy accepted name, accepted closeout SHALL, in one ref transaction, create each standard role ref at the head of the legacy ref it replaces and delete that legacy ref, and SHALL bind every worktree on a renamed ref to its new name. Git admission SHALL refuse any other move of a legacy role ref, except deleting one whose standard successor already holds its commit.

#### Scenario: A repository adopted under legacy names

- **WHEN** the committed table names `accepted/train` and `candidate/train` and the accepted root is bound to `accepted/train`
- **THEN** closeout leaves `dev` and `candidate/dev` at the heads those refs had and removes the legacy refs
- **AND** the accepted and candidate worktrees are bound to `dev` and `candidate/dev`.

#### Scenario: A legacy role ref is moved directly

- **WHEN** a user runs `git branch -m accepted/train dev`
- **THEN** Git admission refuses the update with `legacy_role_ref_protected`.

#### Scenario: A legacy role ref duplicates its successor

- **WHEN** the committed table names `integration/dev` as the legacy candidate name, and `candidate/dev` holds the same commit as `integration/dev`
- **THEN** the absorbed-ref retirement deletes `integration/dev`, and Git admission admits that deletion
- **AND** no other legacy role ref is renamed or moved.
