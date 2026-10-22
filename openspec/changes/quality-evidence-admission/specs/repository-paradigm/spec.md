## ADDED Requirements

### Requirement: Authored text is valid text

Authored text that the shared formatter, Markdown lint or prose checks read SHALL be content Git classifies as text. One shared judgement SHALL decide this for all three from Git's classification of the worktree bytes, not from a list of characters, and the format fix SHALL refuse such a file without writing. The `text` and `eol` attributes govern only line-ending conversion, so a valid document that they mark `-text` SHALL pass.

#### Scenario: Authored Markdown holds a NUL byte

- **WHEN** an authored Markdown file contains a NUL byte
- **THEN** source-format, Markdown lint and prose each report `authored_text_binary` for that file, and `lane format --apply` refuses without writing.

#### Scenario: A valid document is marked -text

- **WHEN** `.gitattributes` marks a valid UTF-8 Markdown document `-text`
- **THEN** none of the three checks reports it as binary, and it passes.
