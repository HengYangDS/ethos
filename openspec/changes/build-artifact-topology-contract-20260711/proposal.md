## Why

The full-proof build gate and the contributor command both invoked `uv build`
without an output directory, allowing package artifacts to appear in the
retired repository-root `dist/` home. That contradicts the generated-artifact
topology the same proof is meant to uphold.

## What Changes

- Bind the product build gate to `build/artifacts/python` and clear that
  disposable local-artifact home before each build.
- Give contributors the same canonical package-build command.
- Lock the registry and contributor instruction with focused tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: generated-evidence governance now requires the
  product build gate and contributor path to use the semantic package-artifact
  home.

## Impact

The gate declaration and its packaged projection, contributor guidance, and
governance tests change. No release artifact becomes tracked, no fallback to
`dist/` remains, and no hosted or remote publication behavior changes.
