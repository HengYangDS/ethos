## ADDED Requirements

### Requirement: Release platforms catalog their archives on every hosted commit run

On every hosted commit run, each host-conformance leg whose runner and Python match a declared
release leg SHALL catalog the runtime archive that its install smoke kept, with the release's
inventory owner and its checks. A release platform's inventory step SHALL NOT first run when a
release is published.

#### Scenario: A commit's Windows leg catalogs its archive

- **WHEN** a hosted commit run's Windows host-conformance leg on the release Python keeps its
  runtime archive
- **THEN** that leg catalogs the archive and checks its expected components

#### Scenario: A release leg changes its runner

- **WHEN** a declared release leg moves to another runner or Python
- **THEN** the host-conformance legs that catalog their archives follow that declaration

#### Scenario: A component is missing on a commit

- **WHEN** a host-conformance leg's inventory lacks an expected component that no locked supply can
  declare
- **THEN** that commit's hosted run fails with the missing component named
