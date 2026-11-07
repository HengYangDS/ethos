## ADDED Requirements

### Requirement: The per-file code ceiling is admitted at commit time

`pre-commit` SHALL measure each staged authored regular file of a registered language on its index
blob with the same measure and the same resolved ceiling as the paradigm report, and SHALL refuse
the commit when a file exceeds the ceiling, naming the file, its effective lines and the ceiling, or
when its blob cannot be measured. The paradigm report SHALL keep its whole-tree check.

#### Scenario: A staged file exceeds the ceiling

- **WHEN** a commit stages a source file whose index blob exceeds the per-file code ceiling
- **THEN** `pre-commit` refuses with `pre_commit_code_size_exceeded:<path>:<lines>><ceiling>`

#### Scenario: Only the worktree copy exceeds the ceiling

- **WHEN** the worktree copy of a file exceeds the ceiling but its staged blob does not
- **THEN** `pre-commit` admits the commit

#### Scenario: A staged entry holds no source

- **WHEN** a commit stages a symlink or a gitlink whose path has a registered suffix
- **THEN** `pre-commit` measures no object for it
