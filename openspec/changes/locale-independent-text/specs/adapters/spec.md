## ADDED Requirements

### Requirement: Process text is UTF-8 whatever the host locale

The process adapter SHALL decode a command's text output and encode its text
input as UTF-8 unless the caller declares the encoding that the command always
writes. The host locale SHALL NOT select a process text encoding.

#### Scenario: A host locale differs from UTF-8

- **WHEN** a command writes UTF-8 text on a host whose locale encoding is GBK or
  code page 1252
- **THEN** the adapter returns the same text as on a UTF-8 host
- **AND** text the adapter writes to the command's standard input is UTF-8.
