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

#### Scenario: provider-native projections preserve one semantic contract
- **WHEN** GitLab and GitHub render issue, review, CI/CD, or release surfaces
- **THEN** each projection preserves the same source identity, intent, required
  fields, branch roles, gates, and evidence bindings
- **AND** provider-native syntax and capabilities may differ without requiring
  byte-for-byte files, identical templates, or a lowest-common-denominator UI
- **AND** GitLab and GitHub each retain complete native issue, review, CI/CD,
  release, update, and distribution behavior rather than a primary-plus-mirror split.

## ADDED Requirements

### Requirement: Single Terminal Campaign Publication
Distribution SHALL derive one HEAD-bound `campaign_terminal` predicate without
persisting a campaign state store. It SHALL pass only when the selected terminal
commit has current local full proof, local `candidate/dev` and protected local
`dev` have completed audited promotion to that commit, required records and
owned-lane closeout are verified, and no required gap remains. Before it passes,
every remote ref, tag, release, artifact, and provider-configuration mutation
SHALL be prohibited.

#### Scenario: Campaign is not terminal
- **WHEN** `campaign_terminal` is `block` or `unknown`
- **THEN** `work/*` and `candidate/dev` remain local-only integration state
- **AND** local `dev` is not represented as remote delivery
- **AND** no `proposal/*`, remote protected `dev`, protected default `main`, tag,
  release, artifact, or provider-configuration mutation occurs

#### Scenario: Terminal campaign is published once
- **WHEN** `campaign_terminal` passes for one immutable commit
- **THEN** exactly one `proposal/terminal-convergence` is projected from that
  commit and GitLab and GitHub independently complete full hosted CI/CD for it
- **AND** only then do remote protected `dev` and protected default `main`, the
  release version, and one signed tag advance to that same commit
- **AND** both delivery planes publish identical artifact digests, SPDX SBOM
  digest, and canonical provenance payload digest
- **AND** provider-scoped DSSE signatures bind that same provenance payload
- **AND** `SPDX`, `DSSE`, and `SLSA` name only the exact emitted format,
  envelope, predicate, and verifier-bounded assurance; their presence alone
  claims neither specification conformance nor a SLSA level
- **AND** no second proposal or release sequence is created for this campaign
