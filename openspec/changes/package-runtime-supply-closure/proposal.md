## Why

Wheel construction currently creates a fresh temporary npm project and runs
`npm ci --offline` for every build. That makes a package build depend on the
caller's npm cache even after the repository's exact lock has already been
installed, and the accepted exact HEAD failed on GitLab when `zod-4.4.3.tgz`
was absent from the dropped-identity cache. The same design repeatedly
materializes thousands of OpenSpec dependency files in disposable trees.

## What Changes

- Make the package build consume one explicitly prepared, lock-validated
  OpenSpec production closure instead of running npm inside the Hatch hook.
- Include only production package roots selected by `package-lock.json` in the
  wheel and sdist, preserving the repository lock as the supply authority.
- Fail before artifact construction when the prepared closure is absent,
  incomplete, symlinked, or version-drifted, with one exact provisioning action.
- Remove the per-build npm subprocess, node/npm build bindings, and
  `ethos-openspec-supply-*` temporary tree lifecycle.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `runtime-activation`: immutable package/runtime construction must consume the
  prepared exact OpenSpec production closure without network or ambient cache
  dependence.

## Impact

The change is bounded to the Hatch OpenSpec runtime hook, the existing delivery
pipeline and runtime build-input resolver, package/runtime tests, and the
terminal design route. It does not change OpenSpec semantics, package identity,
runtime activation state migration, hosted identity dropping, Windows ACL
behavior, or adopter repositories.
