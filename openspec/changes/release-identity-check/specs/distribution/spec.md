## ADDED Requirements

### Requirement: Release assembly admits only the tagged commit's bytes

Release assembly SHALL admit a platform upload only when its smoke record names the release head as
its source commit and the tag's version, in its distribution form, as its distribution version. Any
other upload SHALL refuse the release, naming its host.

#### Scenario: Every leg was built from the tagged commit

- **WHEN** every uploaded leg records the release head and the tag's distribution version
- **THEN** assembly admits the legs as before

#### Scenario: A leg was built from another commit

- **WHEN** an uploaded leg records a source commit other than the release head
- **THEN** assembly fails with `release_assets_identity_mismatch:<host>`

#### Scenario: A leg carries another version

- **WHEN** an uploaded leg records a distribution version other than the tag's
- **THEN** assembly fails with `release_assets_identity_mismatch:<host>`
