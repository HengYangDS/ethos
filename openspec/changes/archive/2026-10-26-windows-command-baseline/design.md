# Design

## Context

See [proposal.md](proposal.md).

- **Today's PATH.** `locked_environment` yields `PATH` = alias directory, mise `bin-paths`, then `os.defpath`. On Windows that ends in `.;C:\bin`.
- **The runner's git.** On GitHub's `windows-latest`, `actions/checkout` runs `C:\Program Files\Git\bin\git.exe` (Git 2.56.0.windows.2, run `40232793659`).
  - Git for Windows installs `bin\` with `git.exe`, `bash.exe` and `sh.exe`.
  - It also installs `cmd\` with `git.exe` and the `git-gui` and `gitk` launchers, and no shell.
- **The adopters' tools.** DDWG's suites spawn `git` and `tar`. Windows ships `tar.exe` (bsdtar) in `System32`.

## Goals / Non-Goals

**Goals:**

- Admitted commands on Windows find the host's system commands and the shell-free Git launcher, as POSIX commands find `/usr/bin`.
- The locked tools stay first, and nothing else from the caller's PATH joins.
- One accepted head that names and describes 0.2.0-alpha.15.

**Non-Goals:**

- Changing POSIX behavior, or the other `os.defpath` fallbacks, which read the caller's PATH first.
- Adding a shell, a package manager or the caller's PATH to the locked environment.

## Decisions

- **One pure function.** `host_command_baseline(windows=…, system_root=…, git=…)` returns the baseline from explicit inputs; `shell_free_git_directory(git)` is the one directory check. `locked_environment` is the effectful edge: it reads `SYSTEMROOT` and resolves the Git that ETHOS itself runs.
- **POSIX keeps `os.defpath`.** Adding Git's own directory there would expose, for example, all of `/opt/homebrew/bin`.
- **Windows: System32, the system root, then shell-free Git.** The system directories come from `SYSTEMROOT`, never a literal `C:\Windows`. Without it they are omitted.
- **A shell never joins.**
  - The Git launcher directory joins only when it holds `git.exe` and no `bash.exe` or `sh.exe`.
  - A resolved `bin\git.exe` maps to its sibling `cmd\git.exe` when that exists.
  - Otherwise git stays out, and the adopter's command refuses explicitly instead of finding an unvetted directory.
- **No new requirement text.** The accepted requirement "Locked execution keeps native mise policy" already promises configuration isolation. A new scenario states the baseline. Its text stays unmodified, because a longer requirement would exceed OpenSpec's strict limit of 500 characters.
- **Release entry, as in earlier entries.** Bump the version owner and its projections as exact replacements, and date the entry with the local calendar day on which the tag is created.

## Risks / Trade-offs

- [`System32` holds more commands than POSIX `/usr/bin`] → It is the operating system's own command baseline, and `tar.exe` lives there; the current directory and `C:\bin` leave the PATH.
- [A Git installation without `cmd\`] → Git stays off the PATH and the adopter's command fails with `ENOENT`, as it does today.
- [Hosted proof] → Only DDWG's `windows-latest` verification on the next release exercises an adopter suite on Windows. Until it passes, the fix counts as unproven there.
