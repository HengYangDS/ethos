## ADDED Requirements

### Requirement: Authored text is valid text

Authored text SHALL be complete UTF-8 without NUL. One shared judgement SHALL validate the complete authored-text selection before formatter narrowing. Source-format, Markdown lint and prose SHALL use it; the format fix SHALL refuse malformed bytes without writing. Native checkout attributes SHALL NOT decide text validity. Non-authored bytes SHALL retain their existing verification owner.

#### Scenario: Authored Markdown holds a NUL byte

- **WHEN** an authored Markdown file contains a NUL byte, including after Git's initial binary-detection window
- **THEN** source-format, Markdown lint and prose each report `authored_text_binary` for that file, and `lane format --apply` refuses without writing.

#### Scenario: An authored carrier has malformed UTF-8

- **WHEN** a declared plain-text, INI, vocabulary or canonical extensionless carrier contains malformed UTF-8
- **THEN** source-format reports `authored_text_encoding` with its path before preparing any formatter postimage, and the format fix leaves all source bytes and the index unchanged.

#### Scenario: A valid document is marked -text

- **WHEN** `.gitattributes` marks a valid UTF-8 Markdown document `-text`
- **THEN** none of the three checks reports it as binary, and it passes.

#### Scenario: Non-authored bytes retain their owner

- **WHEN** binary, received, generated, dependency or immutable evidence bytes are present
- **THEN** their existing owner controls verification and the authored-text judgement does not reinterpret or rewrite them.
