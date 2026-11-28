## MODIFIED Requirements

### Requirement: Native trust preflight preserves identity and failure meaning

Host qualification SHALL check required native trust primitives before building
or installing candidate packages. Missing environment, missing executable, process
creation and timeout SHALL remain distinguishable; none permits signing or publication. Native
platform acceptance remains independently required.

#### Scenario: A native prerequisite fails

- **WHEN** native trust or executable preflight fails on a selected platform
- **THEN** no candidate build or installation starts
- **AND** the native failure reason remains visible without retry or permissive fallback

### Requirement: Platform support is established by native delivered behavior

ETHOS SHALL deliver native macOS and Linux support on explicitly declared
architecture and OS baselines: macOS arm64, Linux arm64 and Linux x64. Every declared
platform SHALL publish, and none is served by another platform's runtime. Runtime
identity and tool supply SHALL name the architecture that the interpreter executes.

#### Scenario: A release advertises supported platforms

- **WHEN** a platform is included in the release support declaration
- **THEN** its delivered artifact passes native installation, CLI/MCP and hooks
- **AND** unsupported combinations remain explicit rather than inheriting another platform's proof

#### Scenario: A leg carries another platform's runtime

- **WHEN** a release leg's qualified runtime names a platform other than the host the leg declares
- **THEN** release assembly refuses with `release_assets_distribution_mismatch:<host>`
- **AND** no asset of that release is written.

### Requirement: A runtime archive names its runtime by a digest prefix

A release archive SHALL name its runtime directory with the first 16 hexadecimal digits of the
runtime digest. An archive carrier SHALL resolve that prefix to the full digest from the runtime
manifest and SHALL refuse a directory that is not its prefix. The host store and its selectors
SHALL keep the full digest.

#### Scenario: An archive directory names another runtime

- **WHEN** an archive's runtime directory is not a prefix of the digest its manifest records
- **THEN** runtime selection refuses the archive before any effect.

## RENAMED Requirements

- FROM: `### Requirement: Windows runtime archives fit the Windows path limit`
- TO: `### Requirement: A runtime archive names its runtime by a digest prefix`
