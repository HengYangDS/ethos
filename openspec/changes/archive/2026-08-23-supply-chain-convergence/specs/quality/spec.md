## ADDED Requirements

### Requirement: Controlled supply-chain identities have one owner

Every direct dependency, downloaded tool, runtime, hosted action, and container
image controlled by ETHOS SHALL have exactly one current semantic version owner.
Lockfiles, integrity hashes, generated provider files, and documentation SHALL
be derived or mechanically checked projections of that owner rather than
independent declarations.

#### Scenario: A controlled identity is audited

- **WHEN** repository supply-chain proof inventories current declarations,
  installers, locks, CI projections, and release metadata
- **THEN** each controlled identity resolves to exactly one semantic owner
- **AND** duplicate owners, orphan literals, missing integrity bindings, and
  projection disagreement block proof with their exact paths

### Requirement: Controlled direct inputs use stable current releases

Every controlled direct supply-chain input SHALL resolve to the current stable
release available from its native package manager or authoritative upstream at
verification time. Exact locks, immutable action commits, container digests,
and downloaded-artifact checksums SHALL bind the selected releases.

#### Scenario: A stable release is newer than the declared input

- **WHEN** the authoritative resolver observes a newer stable release for a
  controlled direct input
- **THEN** supply-chain proof reports the declared owner as stale
- **AND** provider projections and integrity material remain invalid until they
  agree with the updated owner

#### Scenario: An upstream has prerelease and stable versions

- **WHEN** the latest upstream version is a prerelease but an earlier stable
  release exists
- **THEN** the stable release remains the selected current version
- **AND** prerelease adoption requires a separate explicit product decision

### Requirement: Environment tools do not become repository authority

Developer environment and binary acquisition tools MAY implement a declared
supply-chain projection only when they replace incumbent machinery and preserve
offline, integrity, runtime, and proof boundaries. They SHALL NOT become a
second dependency graph, task graph, lifecycle, evidence ledger, or installed
ETHOS runtime requirement.

#### Scenario: A tool manager is proposed

- **WHEN** a tool manager can resolve versions but no incumbent owner or
  installer is deleted
- **THEN** the proposal remains a benchmark and is not added to the repository
- **AND** adoption requires a separately proved replacement with net deletion

## MODIFIED Requirements

### Requirement: Supply Chain Evidence

Release proof SHALL produce deterministic package digests, SBOM, provenance,
and provider-specific publication attestations through bounded release owners.
Every generator SHALL be selected through its current unique policy owner; a
mutable tool version embedded in specification prose, documentation, installer
defaults, or generated provider files SHALL NOT become a parallel owner.

#### Scenario: A release artifact is prepared

- **WHEN** terminal full proof and publish readiness run at one immutable HEAD
- **THEN** local package, SBOM, provenance, GitLab, and GitHub observations remain
  separately attributable
- **AND** matching artifact digests are required before a dual-provider release
  is admitted
- **AND** the generator identity and version match the current policy owner
