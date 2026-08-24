## Why

Source-checkout hook installation claims offline determinism but currently treats
`uv.lock` as if it also contained the build and runtime bytes. With an empty uv
cache, the command cannot resolve Hatchling or the production dependencies, so
repair depends on accidental host cache state.

## What Changes

- Require the active source environment to match the repository lock before it
  can supply build or runtime bytes.
- Build the ETHOS wheel with the verified active environment rather than an
  isolated environment that must resolve its backend from cache.
- Derive the immutable runtime by copying that verified environment, pruning it
  to the hash-bound production closure, and installing the exact built wheel.
- Keep uv cache state disposable: an empty cache neither blocks a valid source
  installation nor authorizes a drifted one.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: Define the source environment as verified bootstrap supply,
  distinct from the lock authority, disposable cache, and immutable runtime.

## Impact

- Source-checkout hook runtime construction and its focused unit and package
  acceptance regressions.
- No new resolver, wheelhouse authority, compatibility path, or adopter-specific
  behavior.
