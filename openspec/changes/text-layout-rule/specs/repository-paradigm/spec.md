## ADDED Requirements

### Requirement: Text without a native formatter has one canonical layout

Authored text whose format owner is `repository-canonical-text` SHALL have no blank line at its
start or end, at most one blank line in a row and one final newline, with whitespace-only lines
empty; an empty file SHALL stay empty, and content lines SHALL keep their bytes. `lane format`, the
source-format gate and `pre-commit` SHALL apply this layout in every governed repository.

#### Scenario: A hygiene file holds a doubled blank line

- **WHEN** a tracked `.gitignore` separates two patterns with two blank lines
- **THEN** `ethos lane format --check` and the source-format gate fail, and `--apply` leaves one
  blank line.

#### Scenario: A canonical-text file ends without a newline

- **WHEN** `VERSION` holds its version with no final newline
- **THEN** the check fails, and the fix adds the newline.

#### Scenario: A violation is staged

- **WHEN** a commit stages a canonical-text file with a blank line at its start
- **THEN** `pre-commit` refuses with the file's path and the line that differs.
