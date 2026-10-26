# Proposal

## Why

On Windows, admitted repository commands cannot run the host's own commands. `locked_environment` ends the locked tools' PATH with `os.defpath`. That is `/bin:/usr/bin` on POSIX, which supplies `git` and `tar`; on Windows it is `.;C:\bin`. It holds no system command at all, and it puts the current directory on PATH.

With alpha.14's reporter fix, DDWG's JavaScript behavior suite now runs on GitHub's `windows-latest`. 50 of its 139 tests then fail with `spawnSync tar ENOENT` (292 times in the journal) or `spawnSync git ENOENT` (8 times). Its coverage falls below the floor, while the same suite passes on macOS and Linux (run `40232793659`).

Adopters install only published releases, so the fix ships as 0.2.0-alpha.15.

## What Changes

- The locked tools are followed by the host's own command baseline, which comes from one pure function of explicit inputs.
  - POSIX keeps `os.defpath`.
  - On Windows the baseline is `%SystemRoot%\System32` and `%SystemRoot%`, read from the environment, followed by the directory of the shell-free Git launcher. The baseline drops `.` and `C:\bin`.
- Git's launcher directory joins only when it holds no shell. Git for Windows ships `cmd\git.exe` beside `bin\git.exe`, and `bin\` also holds `bash.exe` and `sh.exe`. A resolved `bin\git.exe` is therefore mapped to its sibling `cmd\` when that launcher exists.
- Without a `SystemRoot`, the Windows baseline is empty rather than a guessed path.
- The release entry: the product version moves to 0.2.0-alpha.15, and the `0.2.0-alpha.15` changelog entry describes this fix.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: the locked execution environment adds the host's own command baseline after the locked tools, and nothing else from the caller's PATH.

## Impact

Code: `src/ethos/adapters/toolchain/mise.py` and its tests. POSIX behavior does not change. The release entry changes `VERSION`, `CHANGELOG.md`, `distributions/npm/package.json`, `package-lock.json` and the version tests. Adopters receive the fix from the published 0.2.0-alpha.15 release. The tag, the hosted release and adopter rebinds follow the landing as separate effects, and DDWG's `windows-latest` verification on that release is the hosted proof. Out of scope: the other `os.defpath` fallbacks, which read the caller's PATH first, and adopters' own Windows suites.
