# Design

## Context

See [proposal.md](proposal.md). `protected_from_untrusted_write` and `protect_for_current_identity`
(`src/ethos/adapters/repo/trust_anchor/filesystem.py`) run two PowerShell scripts with a 30-second
bound and parse their JSON. `process_listing_command` (`src/ethos/adapters/process.py`) returns a
PowerShell argv on Windows and `ps -axww -o command=` elsewhere, and `process_commands`
(`src/ethos/adapters/repo/runtime/retirement.py`) runs it. `run_command` captures stdout in a
temporary file on every platform, and stderr in a pipe except for finite output on POSIX. On a
Windows timeout, `CommandScope.release` kills the leader and then calls `communicate()`, which joins
the stderr reader thread without a bound, as CPython's own `subprocess.run` does.

## Goals / Non-Goals

**Goals:**

- No product code path starts PowerShell, and no Windows timeout waits for a descendant.
- Unchanged decisions: the owner and the write-like allow entries decide protection as today, and a
  missing, malformed or unsupported observation stays unavailable and never reads as protected.

**Non-Goals:**

- Windows job objects to stop descendants. A descendant of a timed-out Windows command keeps
  running, as today; the quality specification names that containment limit.
- New protection semantics, such as deny entries or integrity labels.
- A paradigm rule against platform shells in governed repositories' product code; it needs an
  adopter inventory and is its own Change.
- The 11 direct `subprocess.run` calls in `src/` that bypass `run_command` keep CPython's unbounded
  read after a Windows timeout. Routing them through the process owner, with Ruff's banned-API rule
  keeping them there, is its own Change.

## Decisions

- **pywin32, not ctypes or another dependency.** The research decision stands: pywin32 wraps the
  security descriptor, token and COM APIs and is already locked. Rejected: hand-written ctypes
  structures; psutil, which adds a dependency, does not read ACLs and reads other processes' command
  lines from their memory.
- **A thin native seam.** Three private functions hold every Win32 call: the current identity, a
  path's owner and DACL entries as plain tuples, and an exclusive grant. The decision over those
  facts is platform-neutral Python, so tests on every platform replace the three functions with
  facts; the native functions run only on hosted Windows. pywin32 is imported under
  `sys.platform == "win32"`, which Ty and Pyright treat as unreachable elsewhere.
- **Process token.** The current identity is the process token's user. ETHOS never impersonates, so
  the thread token that `WindowsIdentity.GetCurrent()` would also consult adds nothing.
- **Entries that apply to the object.** An inherit-only entry grants nothing on the object that
  holds it and is skipped; .NET's `GetAccessRules` used to count it. Allow entries, plain or object,
  with any of write or append data, write extended attributes or attributes, delete, delete child,
  write DAC, write owner, generic write or generic all, name a writer. Deny entries are ignored, as
  before, because they only remove authority. An entry type pywin32 cannot decode, such as a
  conditional callback entry, makes the observation unavailable; .NET silently skipped callback
  entries.
- **WMI on a bounded worker thread.** `win32com.client.GetObject("winmgmts:")` queries
  `Win32_Process.CommandLine` on a daemon thread that initializes COM for itself; the caller waits
  at most the existing 10 seconds. A query error or the bound is `hook_runtime_consumers_unknown`; a
  stuck query leaves only its daemon thread.
- **Files instead of pipes on Windows.** `run_command` captures Windows stderr in a temporary file,
  as finite output already is on POSIX, and reads both files after the leader exits. A descendant
  that keeps the file open cannot block the read, so the post-kill `communicate()` is deleted rather
  than bounded: with no pipe it would only overwrite the captured timeout output.
- **Supply before landing.** The GitLab supply image hashes `uv.lock`, and four earlier Changes
  (`ci-supply-input-refresh`, `supply-image-ci-mode`, `ci-supply-alpha-19`, `probe-supply-binding`)
  each left GitLab refusing the landed head until a later binding, because the hosted `supply_image`
  build runs only from `dev`. The build is admitted from a proposal ref as well, so this lane
  publishes its lock change as its proposal, builds the image from that commit, binds the digest in
  `.config/ci/pipeline.cue` and lands both together. The binding commit changes no hashed input, so
  the image built from the lock commit serves it. A proposal ref reaches a peer only through ETHOS
  publication, which requires the head's proof, as `dev` does.
- **Native test fixtures.** Windows-only tests plant a foreign writer with `icacls`, a native
  program that takes the path and grant as arguments and starts no shell.

## Risks / Trade-offs

- [Windows behavior cannot be proven on macOS or Linux] → The native cases run on hosted Windows x64
  and ARM64 before landing, from a proposal ref; local runs prove the platform-neutral decision and
  the POSIX cases.
- [Coverage on Linux] → The native functions are uncovered there; they are small, and their decision
  logic is covered on every platform.
- [The lock changes] → The GitLab supply image hashes `uv.lock`, so the lane rebuilds the image and
  binds its digest before its proof.

## Migration Plan

One lane, verified on hosted Windows before landing. Rollback is the previous release.
