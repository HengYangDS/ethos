## ADDED Requirements

### Requirement: A release names each declared platform that it does not publish

The release legs SHALL be declared once, each as required or optional, and the release workflow and
its assembler SHALL read that declaration. Publication SHALL refuse a missing required platform and
an artifact for an undeclared platform. A declared optional platform that a release does not publish
SHALL be named, with its cause, in the assembler's output and in the release notes, with the rule
that an adopter installing ETHOS on it keeps its current release.

#### Scenario: An optional leg fails before it uploads

- **WHEN** a declared optional release leg fails before it uploads its artifact
- **THEN** the release publishes the other platforms
- **AND** `left-out.json` names that platform with the cause `leg_incomplete`
- **AND** the release notes name it and state the adopter rule

#### Scenario: A required leg publishes nothing

- **WHEN** a declared required release leg uploads no admitted archive
- **THEN** assembly fails with `release_assets_platform_missing:<host>`

#### Scenario: An artifact names an undeclared platform

- **WHEN** an uploaded artifact names a platform that no release leg declares
- **THEN** assembly fails with `release_assets_host_undeclared:<host>`

#### Scenario: The workflow tolerates only optional failures

- **WHEN** the release workflow is projected from the declared legs
- **THEN** only the optional legs may fail without failing the run
- **AND** the assembler receives exactly the declared required and optional platforms
