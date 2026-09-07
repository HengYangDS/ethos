## MODIFIED Requirements

### Requirement: Product version has one repository authority

ETHOS SHALL keep one tracked SemVer product-version value, SHALL advance that
value whenever an accepted product change adds, removes, or changes observable
product semantics not represented by the current prerelease identity, and SHALL
derive every publishable distribution version and manifest projection from that
value.

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

## ADDED Requirements

### Requirement: Prepared Node supply identity is dependency-bound

ETHOS SHALL validate a reusable prepared Node supply against the locked
`node_modules/*` dependency closure and SHALL NOT treat root or linked workspace
metadata as installed dependency bytes.

#### Scenario: Product version advances without dependency change

- **WHEN** the repository product version changes while every locked
  `node_modules/*` package entry remains identical
- **THEN** the existing prepared Node supply remains valid
- **AND** ETHOS does not require another install or another supply tree.

#### Scenario: Installed dependency changes

- **WHEN** any locked `node_modules/*` package entry differs from the prepared
  supply lock
- **THEN** ETHOS rejects that supply as a lock mismatch.
