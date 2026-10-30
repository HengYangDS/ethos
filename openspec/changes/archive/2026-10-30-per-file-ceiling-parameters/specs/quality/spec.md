## MODIFIED Requirements

### Requirement: Current Markdown stays within one navigable topic

Every tracked, current, hand-authored Markdown documentation file in ETHOS or a governed
repository, including an active OpenSpec Change's proposal, design, tasks and delta specs, SHALL
contain at most as many nonblank physical lines as its repository's effective Markdown ceiling,
500 by default. The release-contract changelog, accepted OpenSpec specifications, the immutable
OpenSpec archive and declared generated output SHALL retain their own carrier-specific checks.

#### Scenario: A current topic exceeds the ceiling

- **WHEN** a tracked current authored Markdown document exceeds its repository's effective
  Markdown ceiling
- **THEN** the quality floor reports that exact source and blocks acceptance
- **AND** frontmatter, code fences, tables and quoted material count
- **AND** adding blank lines or relabeling current content as history does not
  satisfy the requirement

#### Scenario: A repository declares its Markdown ceiling

- **WHEN** a repository's `[paradigm.size]` declares `markdown_nonblank_lines = 400`
- **THEN** a current authored document with 450 nonblank lines is reported against the
  400-line ceiling

#### Scenario: Release history grows without a document-length limit

- **WHEN** the release-contract changelog exceeds 500 nonblank lines in total
  or within a single version section
- **THEN** the documentation length rule does not block that release history
- **AND** release-format obligations remain independent; a same-named ordinary
  document still exceeds the default ceiling at 501 nonblank lines

#### Scenario: An active Change artifact exceeds the ceiling

- **WHEN** an active Change's design or delta spec has 501 nonblank lines in a repository that
  declares no Markdown ceiling
- **THEN** the quality floor reports that exact artifact and blocks acceptance
- **AND** passing official strict validation does not satisfy the requirement

#### Scenario: A normative OpenSpec carrier exceeds the document ceiling

- **WHEN** an accepted specification or an archived Change artifact exceeds 500
  nonblank lines
- **THEN** the documentation length rule does not block it solely for that count
- **AND** official OpenSpec validation, warnings, and semantic capability review
  retain their own authority

#### Scenario: A complex topic needs more space

- **WHEN** one topic cannot fit without losing necessary meaning
- **THEN** it is divided at coherent semantic responsibilities with a README
  route and repaired links, while retaining the original owner relationship
- **AND** arbitrary numbered fragments, copied paragraphs or hidden content
  do not count as progressive disclosure
- **AND** still-live obligations from a shortened source have an identified
  surviving canonical owner; exact Git recoverability alone does not prove
  semantic preservation
