## MODIFIED Requirements

### Requirement: Product version has one repository authority
ETHOS SHALL keep one tracked SemVer product-version value, SHALL advance that
value whenever accepted product semantics advance incompatibly with the prior
prerelease identity, and SHALL derive every publishable distribution version
and manifest projection from that value.

#### Scenario: Repository manifests are inspected
- **WHEN** Python, root workspace, and launcher package metadata are compared
- **THEN** they resolve to the one product-version authority
- **AND** no manifest retains an independently editable product-version literal.

#### Scenario: Accepted prerelease semantics advance
- **WHEN** a newly accepted runtime contains product semantics not represented
  by the previously accepted prerelease
- **THEN** the repository product version advances to a greater SemVer value
- **AND** exact source and artifact digests remain additional identities rather
  than substitutes for that version.

### Requirement: Exact Node Runtime Compatibility Policy

ETHOS SHALL keep exact current LTS and current npm-launcher compatibility
releases in one repository policy and SHALL execute hosted compatibility
acceptance through one reusable runner rather than provider-inline npm command
bodies.

#### Scenario: Hosted npm compatibility is executed for an exact release

- **WHEN** a hosted npm compatibility job runs
- **THEN** `.config/checks/node/runtime.toml` declares Node 24.20.0 and Node
  26.8.1 as the exact compatibility set
- **AND** the provider selects one declared release through `NODE_VERSION`
- **AND** the installer verifies the selected official archive against a
  policy-pinned SHA-256 value before extraction
- **AND** `tools/ci/scripts/run-node-compatibility.sh` rejects an active-runtime
  mismatch before npm executes
- **AND** the runner enables npm engine-strict behavior and executes
  `npm ci --ignore-scripts`, `npm run ethos -- --version`, and
  `npm run test:npm` in that order
- **AND** hosted provider YAML invokes the reusable owner instead of restating
  the acceptance command body.

### Requirement: Reviewed Node Default Promotion

ETHOS SHALL keep compatibility expansion separate from hosted packaging-default
promotion and SHALL require a reviewed change for any default transition.

#### Scenario: Compatibility expands without promoting packaging

- **WHEN** a Node release is added only to hosted compatibility verification
- **THEN** the existing runtime policy and npm packaging default remain
  unchanged
- **AND** promotion requires current release-status verification, successful
  hosted compatibility results, package evidence, and a separate reviewed
  repository change.

#### Scenario: Current stable release becomes the packaging default

- **WHEN** Node 26.8.1 has current upstream release evidence and passes the
  declared hosted compatibility acceptance
- **THEN** Node 26.8.1 becomes the runtime policy and npm packaging default
- **AND** Node 24.20.0 remains the exact LTS compatibility release
- **AND** future default changes still require current release-status
  verification, package evidence, and a separate reviewed repository change.
