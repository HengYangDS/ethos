## Context

The runtime image owner copies an exact standalone interpreter before installing
the locked dependency closure and ETHOS wheel into that image. POSIX standalone
CPython already places its executable and console scripts together under `bin`.
Windows standalone CPython instead places `python.exe`, `Lib`, `DLLs`, and
`python*.dll` at the interpreter root while installers place console scripts
under `Scripts`.

The accepted implementation moves the Windows executable to
`Scripts/python.exe` but leaves the rest of the standalone image at the root.
GitHub exact-HEAD jobs `99700081278`, `99700081420`, and `99700081485` reproduce
the resulting `hook_runtime_entrypoint_missing` boundary on Python 3.13, 3.14,
and 3.12 respectively.

## Goals / Non-Goals

**Goals:**

- preserve one native standalone-interpreter layout on every platform;
- derive Python, scripts directory, and ETHOS entrypoint paths from one layout
  authority;
- validate the generated Windows entrypoint against the copied interpreter;
- delete the venv-shaped Windows assumption without a compatibility route.

**Non-Goals:**

- a generic launcher abstraction, PATH fallback, wrapper script, or executable
  discovery registry;
- changes to Python dependency selection, package supply, or runtime identity;
- the independent GitLab identity-drop `git_process_spawn_failed` failure;
- tempfile scavenging or repository-wide module and documentation layout work.

## Decisions

### 1. Preserve the source interpreter's native root relationship

The copied Windows executable remains at `python/python.exe`, adjacent to
`Lib`, `DLLs`, and native runtime DLLs. POSIX remains `python/bin/python` with
its existing standard-library layout.

Alternative rejected: copy DLLs and the standard library under `Scripts` to
match the current executable location. That would invent a venv-like image
instead of preserving the already-owned standalone distribution.

### 2. Resolve the scripts directory once

The runtime selection owner exposes the platform-native scripts directory.
Python and entrypoint resolution consume that owner: POSIX Python is inside
`bin`, Windows Python is at the interpreter root, and Windows console scripts
are inside `Scripts`.

Alternative rejected: probe several candidate paths or retain the old path as
a fallback. A fallback would conceal malformed runtime generations and create a
second selection rule.

### 3. Keep native Windows launchers

The locked installer remains responsible for producing `ethos.exe`. Runtime
materialization validates that exact file and executes it during generation
smoke. Only POSIX text launchers are rewritten for relocation.

Alternative rejected: synthesize a `.cmd`, Python, or shell wrapper on Windows.
That would add a second launcher owner and would not prove the installed native
entrypoint.

## Risks / Trade-offs

- [Existing tests encode the old path] → Replace their asserted Windows layout
  and retain explicit negative coverage for missing Python and entrypoint files.
- [A pre-existing malformed generation could appear reusable] → Runtime digest
  and manifest validation include file paths, so the corrected image has a new
  identity and the old image cannot satisfy the new expected inventory.
- [Hosted behavior differs from local POSIX execution] → Require the focused
  platform-layout RED locally and exact GitHub Windows 3.12/3.13/3.14 results at
  closeout.

## Migration Plan

1. Add a focused RED that requires Windows `python.exe` at the image root and
   `ethos.exe` under `Scripts`.
2. Move the copied executable to the native root and centralize scripts-path
   resolution; delete the old `Scripts/python.exe` assumption.
3. Run focused runtime selection/materialization tests and the isolated-wheel
   architecture smoke on the available host.
4. Complete exact-HEAD proof, archive/reproof, immutable runtime activation,
   dual-remote publication, and hosted Windows three-version verification.
