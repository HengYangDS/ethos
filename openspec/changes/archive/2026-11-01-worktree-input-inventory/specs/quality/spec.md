## ADDED Requirements

### Requirement: Candidate quality input is what the worktree holds

Candidate quality, formatting and configuration inputs SHALL be the tracked and nonignored untracked
files present in the worktree. A tracked file deleted in the worktree SHALL NOT be candidate input,
whether or not its deletion is staged. Exact committed execution SHALL keep its independent
source-correspondence check.

#### Scenario: A lane deletes a tracked file without staging the deletion

- **WHEN** a governed worktree deletes a tracked file and leaves the deletion unstaged
- **THEN** candidate quality and formatting inputs omit that path instead of refusing it as
  unreadable
- **AND** staging the deletion does not change the selected inputs
- **AND** a proof of the committed head still refuses while one of its subjects is missing

### Requirement: A JavaScript test-scope refusal names its files

When the native runner's enqueued test files differ from the selected test files, the refusal SHALL
name each selected file it never entered and each file it entered unselected.

#### Scenario: A selected test file holds no tests

- **WHEN** a selected JavaScript test file is a shared helper that defines no tests
- **THEN** the behavior gap names that file's repository-relative path
- **AND** declaring the helper `ethos-role=tooling` removes it from the selected tests
