## ADDED Requirements

### Requirement: Windows runtime archives fit the Windows path limit

A release archive SHALL name its runtime directory with the first 16 hexadecimal digits of the
runtime digest, so that its Windows interpreter path stays within 64 characters. An archive carrier
SHALL resolve that prefix to the full digest from the runtime manifest and SHALL refuse a directory
that is not its prefix. The host store and its selectors SHALL keep the full digest.

#### Scenario: A deep install root runs the interpreter

- **WHEN** a Windows host installs the archive under a 157-character install root
- **THEN** the interpreter path is 205 characters and Windows starts the interpreter.

#### Scenario: The archive layout outgrows the budget

- **WHEN** the release builder lays out a Windows archive whose interpreter path inside the archive
  exceeds 64 characters
- **THEN** the distribution tests fail before a release is built.

#### Scenario: An archive directory names another runtime

- **WHEN** an archive's runtime directory is not a prefix of the digest its manifest records
- **THEN** runtime selection refuses the archive before any effect.
