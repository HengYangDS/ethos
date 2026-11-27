## ADDED Requirements

### Requirement: A release tag is re-created from its repaired line

ETHOS SHALL plan the re-creation of a repaired release tag only from a checkout that stands at the
tag's mapped commit, or at the accepted branch's head with the mapped commit among its ancestors.
Any other checkout SHALL refuse that tag by name, at the preview as at the apply. Tags asked from
the accepted head whose targets map to different commits SHALL be re-created under one plan.

#### Scenario: The asking checkout is not on the repaired line

- **WHEN** a re-tag is asked from a checkout that is neither at the tag's mapped commit nor at the
  accepted branch's head above it
- **THEN** that tag refuses with `release_retag_checkout_unrelated` at the preview
- **AND** no ref moves

#### Scenario: A batch maps to different commits

- **WHEN** a re-tag batch asked from the accepted head names tags whose targets map to different
  commits
- **THEN** every tag is re-created under one plan digest
- **AND** each tag peels to its mapped commit and verifies
