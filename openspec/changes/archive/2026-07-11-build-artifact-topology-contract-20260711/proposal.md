## Why

The full-proof build gate and the contributor command both invoked `uv build`
without an output directory, allowing package artifacts to appear in the
retired repository-root `dist/` home. That contradicts the generated-artifact
topology the same proof is meant to uphold.

## What Changes

- Bind the product build gate to `build/artifacts/python` and clear that
  disposable local-artifact home before each build, without asking `uv` to
  create a redundant output-local `.gitignore`.
- Give contributors the same canonical package-build command.
- Lock the registry and contributor instruction with focused tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: subject=package-build-artifact-routing; reuse=extend;
  change=modify; facet:lifecycle=validation; facet:surface=package;
  facet:authority=source

Generated-evidence governance now requires the
product build gate and contributor path to use the semantic package-artifact
home.

## Out Of Scope

- Hosted CI execution, remote publication, and release delivery.
- New artifact lifecycle classes, build runners, exceptions, or compatibility
  routes for the retired repository-root dist/ home.

## Impact

The gate declaration and its packaged projection, contributor and release
guidance, CI projections, coupling registry, and governance tests change. No
release artifact becomes tracked, no fallback to `dist/` remains, and no hosted
or remote publication behavior changes.
