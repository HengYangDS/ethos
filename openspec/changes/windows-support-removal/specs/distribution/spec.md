## MODIFIED Requirements

### Requirement: Native trust preflight preserves identity and failure meaning

Host qualification SHALL check required native trust primitives before building or installing
candidate packages. Missing environment, missing executable, process creation and timeout SHALL
remain distinguishable; none permits signing or publication. Native platform acceptance remains
independently required.

#### Scenario: A native prerequisite fails

- **WHEN** native trust or executable preflight fails on a selected platform
- **THEN** no candidate build or installation starts
- **AND** the native failure reason remains visible without retry or permissive fallback

### Requirement: Platform support is established by native delivered behavior

ETHOS SHALL deliver native macOS and Linux support on explicitly declared architecture and OS
baselines: macOS arm64, Linux arm64 and Linux x64. Every declared platform SHALL publish, and none
is served by another platform's runtime. Runtime identity and tool supply SHALL name the
architecture that the interpreter executes.

#### Scenario: A release advertises supported platforms

- **WHEN** a platform is included in the release support declaration
- **THEN** its delivered artifact passes native installation, CLI/MCP and hooks
- **AND** unsupported combinations remain explicit rather than inheriting another platform's proof

#### Scenario: A leg carries another platform's runtime

- **WHEN** a release leg's qualified runtime names a platform other than the host the leg declares
- **THEN** release assembly refuses with `release_assets_distribution_mismatch:<host>`
- **AND** no asset of that release is written.

#### Scenario: A command starts on a host that ETHOS does not support

- **WHEN** an `ethos` command starts on a host other than macOS or Linux
- **THEN** it refuses with `host_platform_unsupported:<platform>`
- **AND** it observes and changes nothing

### Requirement: A runtime archive names its runtime by a digest prefix

A release archive SHALL name its runtime directory with the first 16 hexadecimal digits of the
runtime digest. An archive carrier SHALL resolve that prefix to the full digest from the runtime
manifest and SHALL refuse a directory that is not its prefix. The host store and its selectors SHALL
keep the full digest.

#### Scenario: An archive directory names another runtime

- **WHEN** an archive's runtime directory is not a prefix of the digest its manifest records
- **THEN** runtime selection refuses the archive before any effect.

### Requirement: A published runtime archive declares what it ships

Each hosted release SHALL publish two inventories for every runtime archive: an SPDX 2.3 SBOM and a
Syft JSON inventory with Go symbols, each naming the archive's published file and SHA-256 and
listing its components. Publication SHALL refuse any archive whose inventories name another digest
or file or are declared twice, refuse an archive without both, and attest them.

#### Scenario: An archive's inventories match its bytes

- **WHEN** a release leg's inventories name its archive's published name and digest and list its
  expected components
- **THEN** the release publishes both beside the archive, covered by `SHA256SUMS` and the build
  provenance attestation

#### Scenario: An archive lacks one of its inventories

- **WHEN** a release leg uploads its archive with only one of its two inventories
- **THEN** assembly fails with `release_assets_inventory_invalid:<host>`
- **AND** no asset of that release is written

#### Scenario: A binding does not match

- **WHEN** any release leg's inventory names another digest or file, or a second declaration sits
  beside the two
- **THEN** assembly fails with `release_assets_inventory_mismatch:<host>`

#### Scenario: A one-package SBOM

- **WHEN** an inventory lists only the archive itself
- **THEN** assembly fails with `release_assets_inventory_components_missing:<host>`

#### Scenario: An expected component is missing

- **WHEN** the catalog lacks the locked `uv` crate, a declared Go tool's module or a shipped Python
  distribution
- **THEN** the inventory owner refuses and names the missing component

#### Scenario: The catalog finds the executable itself

- **WHEN** the catalog already lists Node at the shipped path
- **THEN** the inventory owner declares nothing for it

### Requirement: A release publishes every declared platform

The release legs SHALL be declared once, and the release workflow and its assembler SHALL read that
declaration. Publication SHALL refuse a declared platform that published nothing and an artifact for
an undeclared platform.

#### Scenario: A required leg publishes nothing

- **WHEN** a declared release leg uploads no admitted archive
- **THEN** assembly fails with `release_assets_platform_missing:<host>`

#### Scenario: An artifact names an undeclared platform

- **WHEN** an uploaded artifact names a platform that no release leg declares
- **THEN** assembly fails with `release_assets_host_undeclared:<host>`

#### Scenario: The workflow tolerates no failed leg

- **WHEN** the release workflow is projected from the declared legs
- **THEN** a failed leg fails the run
- **AND** the assembler receives exactly the declared platforms

## RENAMED Requirements

- FROM: `### Requirement: Windows runtime archives fit the Windows path limit`
- TO: `### Requirement: A runtime archive names its runtime by a digest prefix`
- FROM: `### Requirement: A release names each declared platform that it does not publish`
- TO: `### Requirement: A release publishes every declared platform`
