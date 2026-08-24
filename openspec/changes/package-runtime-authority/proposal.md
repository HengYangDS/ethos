## Why

A repository can retain an intact but obsolete hook launcher whose embedded runtime path is no longer the accepted package authority. When `ethos` is also absent from `PATH`, the stale hook can block an exact signed operation while offering no executable route to prove or repair the current HEAD.

## What Changes

- **BREAKING** Replace runtime-digest paths embedded in generated hook launchers with one validated Git-common-dir `CURRENT` selector for an immutable package runtime.
- Activate `CURRENT` only after the candidate runtime, manifest, entrypoint, and complete hook bundle pass validation; malformed or absent selection fails closed.
- Make hooks, public runtime inspection/repair, and proof remediation derive executable commands from the same selected package runtime without ambient `PATH` lookup.
- Emit one absolute, copyable, exact-HEAD remediation command when proof admission blocks a hook operation.
- Retire direct-runtime launcher parsing and include the selected runtime as the sole active consumer in runtime garbage collection.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: Define the selected immutable package runtime as the sole executable package authority outside a source checkout.
- `repository-governance`: Make Git-common runtime selection, hook execution, diagnosis, repair, and proof remediation one fail-closed authority.

## Impact

- Runtime installation and hook activation under the Git common directory.
- Hook launchers, runtime currentness observation, repair commands, proof next actions, and runtime garbage collection.
- Package-install and hook regression tests; no adopter-specific policy or second runtime registry.
