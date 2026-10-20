## MODIFIED Requirements

### Requirement: Text formatting uses the common formatters

Markdown and YAML SHALL be formatted by Prettier, TOML by Taplo and Python by Ruff. Each formatter SHALL be bound through the repository's `fix` and `check` verbs, with configuration under `.config/checks/` declaring the common settings. Blank lines SHALL be what these formatters write for the parsed structure. The paradigm SHALL NOT add a layout rule of its own, so container structure that the formatter accepts conforms.

#### Scenario: Markdown is only linted

- **WHEN** a repository tracks Markdown and has no Prettier configuration in the configuration plane
- **THEN** the paradigm reports a missing Markdown formatter binding.

#### Scenario: Python is not formatted

- **WHEN** a repository tracks Python and has no Ruff configuration in the configuration plane
- **THEN** the paradigm reports a missing Python formatter binding.

#### Scenario: Blank lines pad a document

- **WHEN** a Markdown document separates two paragraphs with two blank lines
- **THEN** the `check` verb fails, and `fix` leaves one blank line.

#### Scenario: The formatter keeps a loose list

- **WHEN** a Markdown list separates its one-paragraph items with blank lines
- **THEN** `check` passes, two `fix` passes leave the document unchanged, its items still render as paragraphs, and the paradigm reports no gap.

#### Scenario: A formatter setting differs

- **WHEN** a repository's Prettier configuration sets `proseWrap` to `always`
- **THEN** the paradigm reports the carrier and the common setting it must declare.

#### Scenario: Only archived files use a carrier class

- **WHEN** a repository's only Python files sit under its immutable OpenSpec archive
- **THEN** the paradigm requires no Ruff binding.

### Requirement: Formatter inputs respect declared carrier ownership

A formatter's declared inputs SHALL exclude carriers that already have another declared owner, such as official OpenSpec artifacts. Those carriers SHALL keep their own owner and checks, layout included.

#### Scenario: A carrier has an official owner

- **WHEN** a repository declares its OpenSpec artifacts official-owner-only
- **THEN** the Markdown formatter's inputs exclude them, their own checks still run, and no other rule lays them out.

## REMOVED Requirements

### Requirement: Markdown layout follows parsed structure

**Reason**: The paradigm's own blank-line rule duplicated the shared formatter's authority. It rejected layout that Prettier accepts, tightened loose lists of one-block items and so changed their rendered meaning, and laid out carriers outside the formatter's inputs, such as evidence records and official OpenSpec artifacts.

**Migration**: Markdown layout is the shared Prettier formatter's output for its declared inputs. `source-format` and the repository's `check` verb report drift, and `ethos lane format --apply` or the `fix` verb repairs it. Adopters drop unapplied `markdown-layout` repairs; repairs that already landed stay valid, because the formatter accepts them.
