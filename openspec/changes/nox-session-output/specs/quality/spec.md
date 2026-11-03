## ADDED Requirements

### Requirement: Nox sessions print their own output

The repository's Nox sessions SHALL NOT print markdown-it's records below info level, which reach
Nox's debug root logger when a session parses Markdown in process. A session's report and
markdown-it's warnings and errors SHALL still print.

#### Scenario: A session parses Markdown in process

- **WHEN** a Nox session runs a provider that parses Markdown with markdown-it
- **THEN** its output holds no markdown-it debug records
- **AND** a markdown-it warning still reaches it
