## MODIFIED Requirements

### Requirement: Host conformance controls repository-local Git semantics

ETHOS SHALL make portable host-conformance assertions independent of ambient
Git configuration and text-conversion defaults by declaring the exact
repository-local semantics required by each fixture. Indexed Git configuration
passed through the process environment SHALL contain a complete key/value pair
for every declared entry on every supported host.

#### Scenario: CRLF bytes are tested on a Windows-style Git configuration

- **WHEN** the adopter fixture stages a CRLF byte sequence while
  `core.autocrlf=true`
- **THEN** its tracked fixture policy preserves the exact bytes in the index
- **AND** the working tree and staged blob round-trip identically.

#### Scenario: Hosted Git subprocess receives a portable configuration overlay

- **WHEN** host-conformance invokes Git on Windows, macOS, or Linux
- **THEN** every indexed `GIT_CONFIG_KEY_n` has a corresponding non-empty
  `GIT_CONFIG_VALUE_n`
- **AND** global and system configuration remain hidden
- **AND** credential prompting remains disabled.
