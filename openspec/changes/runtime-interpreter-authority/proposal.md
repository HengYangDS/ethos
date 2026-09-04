## Why

Runtime activation conflates two different construction inputs: the invoking
lock-current environment that already contains uv and the locked dependency
bytes, and a congruent interpreter whose native files can form a relocatable
Python image. Requiring the latter to be uv-managed rejects valid hosted
runners; assuming that the invoking environment's reported base is always
copyable admits framework and other externally linked layouts. Using either
candidate as the dependency installer discards the available bytes and makes an
offline build depend on accidental cache contents.

This regressed an earlier product invariant: `uv.lock` selects versions, the
authenticated invocation environment supplies the selected bytes, one
capability-admitted congruent interpreter supplies only the native Python
image, and ownership begins at the sealed immutable runtime. A package-manager
brand or disposable cache cannot decide correctness.

## What Changes

- Define interpreter admission by observed Python identity, direct-prefix
  relation, and copyable native-image capability—not by ancestry or installer
  brand.
- Try the invocation's reported base first; if it is not a relocatable image,
  use the authenticated invoking Python only to enumerate already-installed
  candidates offline, then deterministically select a congruent admitted image.
  Keep the invoking interpreter as the separate dependency supply and
  locked-tool execution boundary.
- Verify the invocation environment against the lock, export one hashed
  production closure, project its installed distribution bytes into the
  congruent generated image, strictly prune that image offline, and install the
  exact ETHOS wheel without dependencies.
- Reuse this dependency-supply owner in package acceptance and delete the
  duplicate delivery-specific supply and cache authority.
- Remove offline runtime construction's attempt to install another Python and
  retain fail-closed behavior when interpreter identity or dependency-byte
  provenance is invalid.
- Make each hosted host-conformance toolchain establish an exact native-image
  supply before activation: GitHub provisions the matrix Python into a bounded
  uv installation root, while GitLab consumes the direct Python already owned
  by its digest-pinned image.
- Cover source, installed-package, macOS, Linux, and Windows activation without
  adding a provider-specific branch, ambient `PATH` fallback, network retry, or
  interpreter installation inside activation, second cache, or compatibility
  supply.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `runtime-activation`: immutable runtime construction separates the verified
  dependency environment from its capability-admitted native image, projects
  the locked closure without cache authority, and never installs Python during
  activation.

## Impact

The Python identity observer, dependency-supply and image materializers,
package acceptance, hosted toolchain projections, focused runtime tests, and
runtime-activation specification change. The public runtime identity,
dependency selection, selector transaction, and CI-provider-independent
activation behavior remain unchanged.
