## ADDED Requirements

### Requirement: A push refuses the protected peer identity it adds

Under `peer_identity.mode = "required"`, read at the commit that push admission trusts, push
admission SHALL read the commits a push adds beyond every tip its peer advertises and a pushed tag's
message, and SHALL refuse a fed host, a fed full path, a port after any host and a closed context
with a fed value of any protected peer, as `peer_identity_literal:<form>:<n>:<m>:<line>`. No gap
SHALL carry a value, and no history beyond the advertisement SHALL be read.

#### Scenario: A push adds a fed literal

- **WHEN** a commit or its message names a protected peer's host and the peer does not yet hold it
- **THEN** push admission refuses with `peer_identity_literal:<form>:<n>:<m>:<line>`
- **AND** the same content passes once the peer advertises it

#### Scenario: The advertisement cannot be read

- **WHEN** the peer's advertisement cannot be read under `required`
- **THEN** push admission refuses with `peer_identity_range_unknown:<remote>`

#### Scenario: The mode is disabled or unread

- **WHEN** the trusted commit's profile declares `disabled`, or its profile cannot be read
- **THEN** push admission reads nothing, and an unread mode is the advisory
  `peer_identity_mode_unread`

### Requirement: A CI backstop checks raw pushes

`ethos hook commit-range --check peer-identity` SHALL check a pushed range in a GitLab job with the
job's own identity variables, SHALL be inert without them, and SHALL exit 1 only on a fed literal
when the mode at the range's base or at the proposed head is `required`.

#### Scenario: A job without its identity variables

- **WHEN** `CI_SERVER_HOST` and the project variables are absent
- **THEN** the check passes as `inert`

#### Scenario: A new branch has no base

- **WHEN** the remote head is zero and no remote-tracking accepted branch exists
- **THEN** the check passes with the advisory `peer_identity_backstop_baseline_missing`

### Requirement: The profile binds the peer identity mode

A repository profile MAY declare `[peer_identity] mode`, `disabled` by default or `required`.
`status` SHALL report a protected peer under `disabled` and an unread mode as advisories, never as
required gaps, and the redaction preview SHALL count the fed literals outside the effective record
roots.

#### Scenario: An adopter turns the mode on

- **WHEN** a profile declares `mode = "required"` once no fed literal lies outside its record roots
- **THEN** its pushes refuse new literals, and `status` reports no peer identity advisory

#### Scenario: Status names a protected peer left unchecked

- **WHEN** a repository has a protected peer and its profile declares `disabled`
- **THEN** `ethos status --json` lists `peer_identity_protected_peer_disabled` in
  `summary.peer_identity_advisories`
- **AND** the advisory never becomes a status `required_gaps` entry
