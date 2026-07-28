## MODIFIED Requirements

### Requirement: Published Distribution Boundary
Distribution SHALL preserve a portable offline boundary without imposing provider, repository layout, or self-profile carrier choice.

#### Scenario: npm package scope is allowlisted
- **WHEN** `ethos prove --gate product-boundary --json` audits distribution manifests
- **THEN** the root workspace package is non-publishable
- **AND** the npm distribution manifest declares an explicit `files` allowlist
- **AND** that allowlist is limited to launcher assets and neutral package docs
- **AND** author, authors, maintainers, and contributors metadata are absent

#### Scenario: package installation occurs offline
- **WHEN** a supported adopter installs from an admitted local artifact
- **THEN** installation requires no provider-specific runtime service

### Requirement: Release configuration advertises only active policy
Provider projections SHALL be symmetric derived views of one portable release contract; a provider file does not become a release truth root.

#### Scenario: Release configuration is loaded

- **WHEN** product or adopter release policy reads `.ethos/release.toml`
- **THEN** protected refs, host surfaces, publication remotes, and attestation
  policy remain available
- **AND** dead `version_source`, `tag_pattern`, and `artifact_glob = "dist/*"`
  fields are not generated or treated as configurable behavior.

#### Scenario: Distribution output is located

- **WHEN** a build or release operation resolves Python artifacts
- **THEN** it uses the canonical `build/artifacts/python` topology
- **AND** root `dist/*` is not advertised as a supported artifact home.

#### Scenario: provider configuration drifts
- **WHEN** a provider projection no longer matches its declared source
- **THEN** drift blocks the projection rather than selecting provider-local policy
