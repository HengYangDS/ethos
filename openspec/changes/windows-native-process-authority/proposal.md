## Why

The package-only Windows hook-install proof narrows `PATH` to Git, but runtime
generation cleanup still starts a bare `powershell.exe` to observe active
consumers.  That native process therefore cannot be created, and the shared
command runner currently misreports the non-Git failure as
`git_process_spawn_failed` while discarding the exact command, working
directory, and operating-system cause.

## What Changes

- Establish one provider-neutral process adapter as the sole owner of exact
  argv execution, environment projection, and process-creation diagnostics.
- Make the Git adapter delegate process creation while retaining only Git
  executable resolution and Git-specific failure vocabulary.
- Resolve Windows PowerShell from the native `SYSTEMROOT` installation for
  runtime-consumer observation and trust-anchor operations, never from ambient
  `PATH`.
- Remove the generic command runner from the Git adapter and migrate every
  current consumer and regression to the replacement owner.
- Prove package-only hook installation with a deliberately narrowed Windows
  `PATH` on Python 3.12, 3.13, and 3.14.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `adapters`: External process execution has one non-Git owner and preserves
  exact process-creation evidence.
- `runtime-activation`: Hook runtime cleanup resolves required native host
  executables independently of ambient `PATH`.

## Impact

The change affects the shared process boundary, Git execution delegation,
OpenSpec invocation, Git-hook command execution, Windows trust-anchor
invocation, hook runtime activation, and their focused tests. It adds no
fallback executable lookup, retry, compatibility facade, persistent state, or
new dependency.
