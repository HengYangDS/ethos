## ADDED Requirements

### Requirement: Structural blank-line contract

ETHOS SHALL use one blank line as the only separator between adjacent semantic
blocks in active governed text carriers. It SHALL reject leading, trailing, and
repeated blank-line runs through the carrier's native formatter where one owns
the language, or through the shared structural reader otherwise. Python SHALL
remain governed only by Ruff's language-native formatting contract.

#### Scenario: active configuration has repeated blank lines

- **WHEN** an active governed configuration or provider projection contains two
  or more consecutive blank lines
- **THEN** its owning quality command fails with a line-addressed diagnostic

#### Scenario: Shell embeds another language

- **WHEN** a Shell carrier contains a heredoc body
- **THEN** the structural reader checks the outer Shell layout without applying
  the Shell blank-line contract inside the embedded body

#### Scenario: Active OpenSpec carrier contains repeated blank lines

- **WHEN** an active OpenSpec spec or Change Markdown carrier contains two or
  more consecutive blank lines
- **THEN** the shared reader reports the repeated blank run without replacing
  official OpenSpec schema validation
