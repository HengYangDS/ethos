## REMOVED Requirements

### Requirement: Text formatting uses the common formatters

**Reason**: It required a tracked formatter carrier in every repository whose carrier class is
present, although the native gates run on the configuration ETHOS ships and add a repository's own
file only as an increment. Its two "missing binding" scenarios therefore demanded copies of shipped
facts. A MODIFIED block cannot drop scenarios, so the requirement moves, without them, to "Text
formatting uses the shipped common formatters".

**Migration**: Read "Text formatting uses the shipped common formatters". A repository may delete a
formatter carrier that only repeats the common settings; one it keeps is still checked.

## ADDED Requirements

### Requirement: Text formatting uses the shipped common formatters

Markdown and YAML SHALL be formatted by Prettier, TOML by Taplo and Python by Ruff through the
repository's `fix` and `check` verbs. ETHOS SHALL ship their common settings; a repository's own
configuration under `.config/checks/` SHALL be optional and SHALL keep those settings. Blank lines
SHALL be what the formatters write, and the paradigm SHALL add no layout rule of its own.

#### Scenario: No local formatter configuration

- **WHEN** a repository tracks Markdown, TOML and Python and keeps no Prettier, Taplo or Ruff
  configuration in the configuration plane
- **THEN** the paradigm reports no formatter gap and the formatters run on the shipped settings

#### Scenario: Blank lines pad a document

- **WHEN** a Markdown document separates two paragraphs with two blank lines
- **THEN** the `check` verb fails, and `fix` leaves one blank line.

#### Scenario: The formatter keeps a loose list

- **WHEN** a Markdown list separates its one-paragraph items with blank lines
- **THEN** `check` passes, two `fix` passes leave the document unchanged, its items still render as
  paragraphs, and the paradigm reports no gap.

#### Scenario: A formatter setting differs

- **WHEN** a repository's Prettier configuration sets `proseWrap` to `always`
- **THEN** the paradigm reports the carrier and the common setting it must declare.

#### Scenario: Only archived files use a carrier class

- **WHEN** a repository's only Python files sit under its immutable OpenSpec archive and it keeps a
  Ruff configuration that differs from the common settings
- **THEN** the paradigm reports no Ruff setting gap.

## MODIFIED Requirements

### Requirement: Released products keep one version source

A repository that publishes releases SHALL keep `VERSION` as its only version source and SHALL tag
releases as `v` followed by a Semantic Versioning version. A root `package.json` `version` equal to
`VERSION` SHALL count as a checked projection, since npm publishes only a literal version; any
other manifest version SHALL count as a second source. `CHANGELOG.md` SHALL follow Keep a Changelog
1.1.0 with an `[Unreleased]` section and bracketed version headings.

#### Scenario: A second version source exists

- **WHEN** a released repository keeps a literal version in `package.json` that differs from
  `VERSION`
- **THEN** the paradigm reports two version sources.

#### Scenario: The npm manifest projects VERSION

- **WHEN** a released repository's root `package.json` declares the version that `VERSION` holds
- **THEN** the paradigm reports no version-source gap
- **AND** the same manifest without `VERSION` reports the missing source.

#### Scenario: A version heading is unbracketed

- **WHEN** `CHANGELOG.md` contains `## 1.2.0 - 2026-10-14`
- **THEN** the paradigm reports a non-standard version heading.
