## MODIFIED Requirements

### Requirement: Text formatting uses the shipped common formatters

Markdown and YAML SHALL be formatted by Prettier, TOML by Taplo and Python by Ruff through the
repository's `fix` and `check` verbs. ETHOS SHALL ship their common settings; a repository's own
configuration under `.config/checks/` SHALL be optional and SHALL keep those settings. Blank lines
SHALL be what the formatters write, except where the Markdown list rule decides them.

#### Scenario: No local formatter configuration

- **WHEN** a repository tracks Markdown, TOML and Python and keeps no Prettier, Taplo or Ruff
  configuration in the configuration plane
- **THEN** the paradigm reports no formatter gap and the formatters run on the shipped settings

#### Scenario: Blank lines pad a document

- **WHEN** a Markdown document separates two paragraphs with two blank lines
- **THEN** the `check` verb fails, and `fix` leaves one blank line.

#### Scenario: The formatter keeps a loose list

- **WHEN** a Markdown list separates its one-paragraph items with blank lines
- **THEN** Prettier alone keeps the lines, and the Markdown list rule refuses the list and removes
  them.

#### Scenario: A formatter setting differs

- **WHEN** a repository's Prettier configuration sets `proseWrap` to `always`
- **THEN** the paradigm reports the carrier and the common setting it must declare.

#### Scenario: Only archived files use a carrier class

- **WHEN** a repository's only Python files sit under its immutable OpenSpec archive and it keeps a
  Ruff configuration that differs from the common settings
- **THEN** the paradigm reports no Ruff setting gap.

## ADDED Requirements

### Requirement: Markdown list items have one blank-line rule

Inside a Markdown list item, a paragraph that follows another block, and a block that follows a
non-paragraph block, SHALL be preceded by one blank line; a block that follows its introducing
paragraph SHALL follow it directly. An item holding such a separator SHALL be followed by one blank
line; any other item SHALL be followed directly by the next. The Markdown fix, check, gate and
`pre-commit` SHALL apply this rule to every authored Markdown file.

#### Scenario: A stray blank line follows a one-paragraph item

- **WHEN** a Markdown list separates its one-paragraph items with blank lines
- **THEN** `check` and the Markdown gate fail with the file and line, `fix` removes the lines, and a
  second `fix` changes nothing.

#### Scenario: A blank line separates a paragraph from the block it introduces

- **WHEN** a list item's paragraph is followed by a blank line and then a nested list or code block
- **THEN** `check` fails, and `fix` joins the block to its paragraph.

#### Scenario: An item holds two paragraphs

- **WHEN** a list item holds two paragraphs and the next item follows it directly
- **THEN** `fix` writes one blank line after the item, and `check` then passes.

#### Scenario: A violation is staged

- **WHEN** a commit stages an authored Markdown file that breaks the list rule
- **THEN** `pre-commit` refuses with the file's path and the line of the first violation.
