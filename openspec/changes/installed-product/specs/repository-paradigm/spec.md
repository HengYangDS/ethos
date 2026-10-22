## MODIFIED Requirements

### Requirement: Text normalization is declared

Every governed repository SHALL keep `.editorconfig` and `.gitattributes` that select UTF-8, LF line endings and a final newline for tracked text. The last `.gitattributes` pattern for every file SHALL be `* text=auto eol=lf`; narrower patterns MAY mark specific carriers as binary or byte-exact, but SHALL NOT give a tracked file CRLF or host-dependent line endings under the attributes that Git resolves.

#### Scenario: Line endings are undeclared

- **WHEN** a governed repository has no `.gitattributes`
- **THEN** the paradigm reports missing text normalization.

#### Scenario: A narrower pattern selects another line ending

- **WHEN** a conforming `.gitattributes` is followed by `run.cmd eol=crlf`, or a nested `.gitattributes` gives `docs/*.md` no `eol`
- **THEN** the paradigm reports each file whose effective attributes select that line ending, with a repair that drops the override or marks the file `-text`
- **AND** a file marked `-text`, `binary` or byte-exact keeps its bytes without a gap.

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

### Requirement: Language tags and received names keep their form

A dot-separated name segment MAY be a BCP 47 language tag in its canonical case. A path that the repository's Git attributes mark `linguist-vendored` or `linguist-generated` is received rather than authored and SHALL keep its name, and so SHALL a directory that holds only such paths. The repair for a name outside kebab-case SHALL name both ways out: renaming it to its kebab-case form, and marking it received when a third party or a generator authored it.

#### Scenario: A localized carrier names its language

- **WHEN** a repository tracks `media/captions.zh-CN.vtt` and `media/transcript.zh-Hans-CN.md`
- **THEN** no name is reported
- **AND** `media/captions.ZH-CN.vtt` is reported, because its language subtag is not lowercase.

#### Scenario: A vendored font keeps its upstream name

- **WHEN** the repository's `.gitattributes` marks `assets/fonts/**` as `linguist-vendored` and the repository tracks `assets/fonts/NotoSansCJKsc-Bold.otf`
- **THEN** no name is reported, and prewrite admits a new file there under its upstream name
- **AND** without that attribute the same name is reported, with a repair that names its kebab-case form and the `linguist-vendored` or `linguist-generated` marking.

## ADDED Requirements

### Requirement: A license grant is a recognized standard text

A governed repository that tracks a root `LICENSE` SHALL keep in it the standard text of one license whose SPDX template the paradigm contract pins by digest, matched as the SPDX matching guidelines describe, unless its package metadata names the license by a `LicenseRef-` identifier. A copyright notice that the template requires SHALL name its holder, and only the template's own title MAY precede it. Which license a repository grants remains its own choice.

#### Scenario: A grant departs from its license

- **WHEN** a repository's `LICENSE` edits or retitles the MIT text, or keeps the template placeholder instead of a copyright holder
- **THEN** the paradigm reports the grant, naming the recognized licenses.

#### Scenario: A license outside the SPDX list is declared

- **WHEN** a repository's `LICENSE` holds its own proprietary terms and its `pyproject.toml` declares `LicenseRef-Proprietary`
- **THEN** the grant conforms, and a `package.json` that declares `MIT` is reported.

### Requirement: A license grant is linked and consistently declared

A repository that tracks a root `LICENSE` SHALL link it from its `README.md`. Every root `package.json`, `package-lock.json` or `pyproject.toml` that declares a license SHALL declare the same SPDX identifier, and a repository SHALL NOT need a package for these checks.

#### Scenario: Metadata names another license

- **WHEN** a repository grants MIT and its `package.json` declares `Apache-2.0`
- **THEN** the paradigm reports the manifest, while a `pyproject.toml` that declares `MIT` conforms.

#### Scenario: A grant stands without a package

- **WHEN** a documentation repository tracks the standard MIT text and its `README.md` links it, with no package manifest
- **THEN** no license gap is reported
- **AND** removing the link reports the public entry.

## REMOVED Requirements

### Requirement: Markdown layout follows parsed structure

**Reason**: The paradigm's own blank-line rule duplicated the shared formatter's authority. It rejected layout that Prettier accepts, tightened loose lists of one-block items and so changed their rendered meaning, and laid out carriers outside the formatter's inputs, such as evidence records and official OpenSpec artifacts.

**Migration**: Markdown layout is the shared Prettier formatter's output for its declared inputs. `source-format` and the repository's `check` verb report drift, and `ethos lane format --apply` or the `fix` verb repairs it. Adopters drop unapplied `markdown-layout` repairs; repairs that already landed stay valid, because the formatter accepts them.
