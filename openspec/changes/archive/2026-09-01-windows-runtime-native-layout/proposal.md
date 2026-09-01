## Why

The accepted package-only runtime constructs Windows standalone CPython with
the executable under `Scripts/` while leaving `Lib` and runtime DLLs at the
interpreter root. GitHub Windows Python 3.12, 3.13, and 3.14 therefore fail the
same isolated-wheel hook-install test before a runtime entrypoint can be
validated.

## What Changes

- Preserve the native standalone CPython layout on Windows: the interpreter
  remains at the runtime root and console scripts remain under `Scripts/`.
- Make Python and console-script path resolution derive from that one platform
  layout instead of assuming a venv layout.
- Add a regression that fails when the Windows runtime root, standard library,
  DLLs, interpreter, and `ethos.exe` entrypoint are not mutually executable.
- Delete the incorrect Windows `Scripts/python.exe` materialization assumption;
  add no compatibility launcher, fallback lookup, or second runtime model.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `runtime-activation`: Immutable runtime materialization preserves the native
  standalone interpreter layout and validates its platform-native entrypoint.

## Impact

- Runtime selection and Python-image materialization under
  `src/ethos/adapters/repo/runtime/`.
- Focused runtime materialization tests and the isolated-wheel architecture
  smoke test.
- The existing terminal convergence plan records this hosted Windows boundary;
  supply ownership, tempfile scavenging, state migration, and general module or
  documentation layout remain independent successors.
