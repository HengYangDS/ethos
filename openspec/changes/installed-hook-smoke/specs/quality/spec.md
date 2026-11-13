## ADDED Requirements

### Requirement: The installed hook admits the product repository

The package-only lifecycle SHALL run the generated `pre-commit` hook under the installed runtime in
a clone of the product repository at the candidate head, so a hook that refuses every commit there
fails `local-install-smoke` before release.

#### Scenario: The installed hook judges staged text in the product repository

- **WHEN** `local-install-smoke` qualifies the clean development build of the head and runs the
  delivered hook in a Work Lane of a product clone with a conforming staged edit
- **THEN** `pre-commit` SHALL exit 0
- **AND** with a staged `.gitignore` that opens with a blank line instead, `pre-commit` SHALL exit
  non-zero and name `pre_commit_text_layout:.gitignore:1`
- **AND** a release or dirty build SHALL record the step as not qualified
