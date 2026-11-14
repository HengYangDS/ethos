## ADDED Requirements

### Requirement: Received paths are not authored inputs

A path that the repository's Git attributes mark `linguist-vendored` or `linguist-generated` is
received and SHALL NOT be an authored input. `lane format`, in its check and apply forms, and the
source-format, Markdown, prose and configuration gates SHALL neither report nor rewrite it. A
format request that names one SHALL be refused with `source_format_other_owner`, as for any path
with another owner.

#### Scenario: An upstream license sits in a vendored tree

- **WHEN** `.gitattributes` marks `vendor/**` `linguist-vendored`, and that tree holds an upstream
  `LICENSE` with a doubled blank line and a Markdown file with trailing spaces, beside an authored
  Markdown file that drifts
- **THEN** `ethos lane format --check` and the source-format gate report `source_format_drift` for
  the authored file only
- **AND** `--apply` rewrites the authored file and leaves the received bytes unchanged.

#### Scenario: A received path is named

- **WHEN** `ethos lane format vendor/font/LICENSE --check` names that license
- **THEN** it refuses with `source_format_other_owner:vendor/font/LICENSE`.

#### Scenario: Received files hold what authored ones may not

- **WHEN** a vendored tree holds a Markdown file with a doubled blank line and a misspelling, and a
  JSON file outside the formatter's layout
- **THEN** the Markdown, prose and configuration gates report nothing for them.
