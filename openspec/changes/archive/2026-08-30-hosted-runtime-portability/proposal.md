## Why

The accepted source passes local proof but its exact-head hosted pipeline fails on
macOS because the Python bootstrap assumes Debian, and on Windows because wheel
construction derives a Node executable path that does not exist in the installed
`nodejs-wheel-binaries` layout. Remote refs are therefore published without the
required cross-platform delivery proof.

## What Changes

- Make the shared Python bootstrap select host prerequisites from the detected
  operating system instead of treating a missing Linux utility as Debian.
- Resolve the locked `nodejs-wheel-binaries` Node and npm coordinates once from
  the installed platform layout and require both inputs to exist before building.
- Reuse that resolver in wheel construction and package-only acceptance tests,
  deleting repeated path assembly.
- Add focused regressions for Darwin bootstrap behavior and both POSIX and Windows
  Node layouts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: Hosted bootstrap and wheel construction must consume valid,
  platform-native prerequisites on Linux, macOS, and Windows.

## Impact

The change is limited to the shared CI bootstrap, the package-build toolchain
resolver, its consumers, and focused distribution tests. It does not change
product semantics, runtime activation, publication authority, tempfile
reconciliation, state migration, or adopter behavior.
