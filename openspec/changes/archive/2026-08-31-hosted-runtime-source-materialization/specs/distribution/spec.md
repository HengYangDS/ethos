## MODIFIED Requirements

### Requirement: Hosted package construction uses platform-native locked inputs

ETHOS SHALL bootstrap hosted prerequisites from the observed operating system
and SHALL resolve `nodejs-wheel` Node/npm inputs through one product-owned,
validated resolver used by every source-build, package-only runtime, OpenSpec,
and delivery consumer. It SHALL NOT infer a Debian host from a missing Linux
utility or reconstruct package paths independently at each caller.

#### Scenario: Darwin bootstrap does not enter Debian installation

- **GIVEN** the shared Python bootstrap executes on Darwin with Git available
- **WHEN** Linux `ldconfig` is unavailable
- **THEN** the bootstrap does not invoke `apt-get`
- **AND** it continues through the repository-locked Python and OpenSpec setup.

#### Scenario: Linux bootstrap repairs supported prerequisites

- **GIVEN** the shared Python bootstrap executes on Linux
- **WHEN** Git, `libatomic.so.1`, or the signing policy's `ssh-keygen` executable
  is missing and `apt-get` is available
- **THEN** it installs only the corresponding declared host prerequisite before
  repository bootstrap continues
- **AND** absence of the selected package manager fails with a precise diagnostic.

#### Scenario: Windows wheel build resolves the installed Node layout

- **GIVEN** `nodejs-wheel-binaries` is installed from the repository lock on Windows
- **WHEN** runtime materialization, OpenSpec, or delivery binds Node inputs
- **THEN** Node resolves to the package-root `node.exe`
- **AND** npm resolves to the package-local `npm-cli.js` when npm is required
- **AND** the coordinates are validated before their consumer executes.

#### Scenario: POSIX wheel build resolves the installed Node layout

- **GIVEN** `nodejs-wheel-binaries` is installed from the repository lock on a
  supported POSIX host
- **WHEN** runtime materialization, OpenSpec, or delivery binds Node inputs
- **THEN** Node resolves to the package-local `bin/node`
- **AND** npm resolves to the package-local `npm-cli.js` when npm is required
- **AND** callers do not reconstruct either coordinate.
