## MODIFIED Requirements

### Requirement: Host conformance keeps local Git semantics exact

Host-conformance fixtures and ETHOS source SHALL declare exact local Git
semantics independent of ambient configuration, repository ownership and text
conversion. Every indexed configuration entry SHALL carry a non-empty key and
value on every supported host. The shared local Git boundary SHALL take
process-environment configuration only from this explicit overlay and SHALL hide
global and system configuration.

#### Scenario: Clean ETHOS checkout has one source tree

- **WHEN** native Linux or macOS checks out one exact ETHOS commit and
  reports no source overlay
- **THEN** source build identity equals that commit's exact tree on every host
- **AND** the repository-owned content policy, not ambient Git configuration,
  defines text normalization

#### Scenario: CRLF bytes are tested under a converting Git configuration

- **WHEN** the adopter fixture stages a CRLF byte sequence while
  `core.autocrlf=true`
- **THEN** its tracked fixture policy preserves the exact bytes in the index
- **AND** the working tree and staged blob round-trip identically.

#### Scenario: Hosted Git subprocess receives a portable configuration overlay

- **WHEN** host-conformance invokes Git on macOS or Linux
- **THEN** every indexed `GIT_CONFIG_KEY_n` has a corresponding non-empty
  `GIT_CONFIG_VALUE_n`
- **AND** global and system configuration remain hidden
- **AND** credential prompting remains disabled.

#### Scenario: Declared trust and identity reach Git exactly

- **WHEN** a caller declares exact repository trust as an indexed configuration
  entry and explicit author and committer identity, and ETHOS then observes
  source identity or creates a commit
- **THEN** Git receives exactly that trust entry and identity through the shared
  subprocess boundary
- **AND** repository-local `user.name` and `user.email` remain unchanged and
  authoritative for identity policy
- **AND** a `safe.directory=*` entry or an incomplete or empty indexed pair fails
  as `git_config_overlay_invalid` before Git runs
- **AND** no ambient user Git configuration participates in the result.
