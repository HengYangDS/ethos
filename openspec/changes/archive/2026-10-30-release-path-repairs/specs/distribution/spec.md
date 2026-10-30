## MODIFIED Requirements

### Requirement: Published Distribution Boundary

Distribution manifests SHALL publish only neutral launcher assets and SHALL NOT
ship historical evidence, host-local state, tests, adopter-private records, or
person attribution metadata as product defaults.

#### Scenario: npm package scope is allowlisted

- **WHEN** `ethos prove --gate product-boundary --json` audits distribution manifests
- **THEN** a root package that declares workspaces is non-publishable
- **AND** the npm distribution manifest declares an explicit `files` allowlist
- **AND** that allowlist is limited to launcher assets and neutral package docs
- **AND** author, authors, maintainers, and contributors metadata are absent

### Requirement: Distribution Adapter Outside Python Packages

ETHOS SHALL keep npm launcher metadata under `distributions/npm` and outside
the Python package workspace.

#### Scenario: npm launcher is checked

- **WHEN** the npm launcher package is inspected
- **THEN** it is the standalone package at `distributions/npm`, not a workspace of the root package
- **AND** it is not included in the Python wheel
- **AND** the launcher forwards to the Python ETHOS command plane

### Requirement: Product version has one repository authority

ETHOS SHALL derive product-release projections from one tracked SemVer 2.0.0
target. Unpublished source iterations MAY share it. Once an explicit release
identity is accepted, changed released semantics SHALL require a greater
version. Source and artifact digests SHALL NOT replace that
release boundary. No dependency lock SHALL record the product version.

#### Scenario: Repository manifests are inspected

- **WHEN** Python, root package, and launcher package metadata are compared
- **THEN** they resolve to the one product-version authority
- **AND** no manifest retains an independently editable product-version literal
- **AND** the root package lock records no product version

#### Scenario: A release advances the product version

- **WHEN** release preparation moves the product version
- **THEN** no dependency lock or supply-image input changes
- **AND** the locked supply image built before it still matches the release checkout

#### Scenario: Unpublished source iterations share a release target

- **WHEN** several accepted source commits precede explicit release
- **THEN** they may retain the same next product-release target
- **AND** their exact development build identities remain distinct

#### Scenario: Accepted prerelease semantics advance

- **WHEN** newly accepted product semantics are selected after an explicitly released prerelease
- **THEN** the product version advances according to the compatibility policy
- **AND** the existing release version and artifacts remain unchanged
