## MODIFIED Requirements

### Requirement: Host conformance controls repository-local Git semantics

ETHOS SHALL make portable host-conformance assertions independent of ambient
Git configuration, repository ownership, and text-conversion defaults by
declaring the exact repository-local semantics required by each fixture and by
the ETHOS source repository itself. Indexed Git configuration passed through the
process environment SHALL contain a complete key/value pair for every declared
entry on every supported host. The shared Git execution boundary SHALL preserve
only that explicit overlay while continuing to hide ambient global and system
configuration.

#### Scenario: Clean ETHOS checkout has one source tree

- **WHEN** native Linux, macOS, or Windows checks out one exact ETHOS commit and
  reports no source overlay
- **THEN** source build identity equals that commit's exact tree on every host
- **AND** the repository-owned content policy, not ambient Git configuration,
  defines text normalization

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

#### Scenario: Hosted proof drops process identity

- **GIVEN** a hosted runner owns the checkout and then executes repository proof
  under a different declared UID and GID
- **WHEN** ETHOS observes source identity or creates a deterministic test commit
- **THEN** Git receives the runner-declared exact repository trust and explicit
  author/committer identity through the shared subprocess boundary
- **AND** repository-local `user.name` and `user.email` remain authoritative for
  identity policy
- **AND** no ambient user Git configuration, broad trust rule, or per-test
  exception participates in the result.
