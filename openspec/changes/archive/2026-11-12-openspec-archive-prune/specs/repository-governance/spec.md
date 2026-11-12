## ADDED Requirements

### Requirement: Pruned archived Changes stay in Git history

A governed Change MAY remove archived Changes from the current tree when no tracked file outside the
archive cites their paths. Git ancestry and the release tags whose trees contain them SHALL keep the
removed Changes readable, so a citation from another archived Change still resolves there, and an
archived Change that stays SHALL NOT be rewritten.

#### Scenario: Archived Changes before a date are pruned

- **WHEN** a governed Change removes the archived Changes dated before a cutoff
- **THEN** no tracked file outside the archive cites a removed path
- **AND** each removed Change stays readable at the commits and release tags that contain it.

#### Scenario: A later document needs a pruned Change

- **WHEN** a document cites a Change that the current tree no longer holds
- **THEN** it cites the release tag and path, and the Change is not restored to the archive.
