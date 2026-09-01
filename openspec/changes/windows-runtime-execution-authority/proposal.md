## Why

The accepted immutable runtime passes native Python relocation checks on
Windows, but all hosted Python 3.12, 3.13, and 3.14 jobs then fail when runtime
post-observation executes the generated `Scripts/ethos.exe`. ETHOS currently
gives that package-generated launcher a second execution authority beside the
owned interpreter already used by Git hooks.

## What Changes

- Make the immutable runtime's sole ETHOS execution authority its owned Python
  executable with `-B -I -m ethos.cli`.
- Use that same command for runtime post-observation and all selected-runtime
  continuation commands.
- Remove the selected console-launcher field and the requirement that a
  generated `ethos`/`ethos.exe` file authorize or validate a runtime.
- Preserve ordinary wheel console scripts as package-install projections; they
  no longer define immutable runtime identity or currentness.
- Prove the boundary locally and on hosted Windows Python 3.12, 3.13, and 3.14.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `runtime-activation`: An immutable runtime is executed and post-observed
  through its owned Python module command rather than a relocated generated
  console launcher.

## Impact

- Runtime selection and materialization under
  `src/ethos/adapters/repo/runtime/`.
- Focused selection/materialization tests and the isolated-wheel architecture
  smoke.
- The terminal runtime/package convergence description.
- No change to external wheel installation, OpenSpec supply, Git history,
  branch roles, publication, tempfile ownership, or adopter repositories.
