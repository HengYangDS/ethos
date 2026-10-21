## ADDED Requirements

### Requirement: Formatted text carriers are Git text

A carrier that a native text formatter owns SHALL be text as Git classifies it: Git SHALL classify its index and worktree content as text, and its attributes SHALL NOT unset `text`. A carrier that keeps exact bytes SHALL be declared byte-bound in the repository's format-selection increment or stay outside the authored inputs, and no list of forbidden characters SHALL decide what is text.

#### Scenario: Authored Markdown holds a NUL byte

- **WHEN** a tracked authored Markdown file contains a NUL byte
- **THEN** the source-format gate reports `source_format_not_text` for that file.

#### Scenario: Authored Markdown is relabeled binary

- **WHEN** `.gitattributes` marks an authored Markdown file `-text`
- **THEN** the source-format gate reports that file, while a byte-bound carrier with the same attribute keeps its bytes and passes.
