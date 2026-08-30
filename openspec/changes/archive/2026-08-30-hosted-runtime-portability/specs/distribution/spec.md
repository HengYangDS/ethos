## ADDED Requirements

### Requirement: Hosted package construction uses platform-native locked inputs

ETHOS SHALL bootstrap hosted prerequisites from the observed operating system
and SHALL resolve wheel-build Node/npm inputs from the installed locked package
layout through one validated owner. It SHALL NOT infer a Debian host from a
missing Linux utility or reconstruct package paths independently at each caller.

#### Scenario: Darwin bootstrap does not enter Debian installation

- **GIVEN** the shared Python bootstrap executes on Darwin with Git available
- **WHEN** Linux `ldconfig` is unavailable
- **THEN** the bootstrap does not invoke `apt-get`
- **AND** it continues through the repository-locked Python and OpenSpec setup.

#### Scenario: Linux bootstrap repairs supported prerequisites

- **GIVEN** the shared Python bootstrap executes on Linux
- **WHEN** Git or `libatomic.so.1` is missing and `apt-get` is available
- **THEN** it installs only those declared host prerequisites before repository
  bootstrap continues
- **AND** absence of the selected package manager fails with a precise diagnostic.

#### Scenario: Windows wheel build resolves the installed Node layout

- **GIVEN** `nodejs-wheel-binaries` is installed from the repository lock on Windows
- **WHEN** the delivery pipeline binds build inputs
- **THEN** Node resolves to the package-root `node.exe`
- **AND** npm resolves to the package-local `npm-cli.js`
- **AND** both coordinates are validated before Hatch build isolation starts.

#### Scenario: POSIX wheel build resolves the installed Node layout

- **GIVEN** `nodejs-wheel-binaries` is installed from the repository lock on a
  supported POSIX host
- **WHEN** the delivery pipeline binds build inputs
- **THEN** Node resolves to the package-local `bin/node`
- **AND** the same validated npm CLI coordinate is used by every build consumer.
