# Proposal

## Why

ETHOS observes and sets Windows ACLs, and lists running processes, by starting Windows PowerShell
from Python. On hosted Windows that path now fails every host conformance job, and the decision to
replace it has waited 40 days for a Change.

- On 2026-09-22 package conformance failed on Windows at
  `git_object_trust_anchor_observation_unavailable:timeout`. The research note written then chose
  pywin32's Win32 security wrappers over another shell retry and recorded that no Change owned the
  work (`docs/research/foundations/effects.md:91-123`).
- Since `ab1ac7e26` every Windows job of `host_conformance` hangs until pytest-timeout's 600-second
  bound (GitHub issue #25). The proposal run of `22f912c2c` (GitHub 41312820863) shows where, in one
  process: `protect_for_current_identity` exceeds its 30-second PowerShell bound, and the timeout's
  cleanup then waits without a bound for the killed command's stderr pipe to close
  (`CommandScope.release`, `process.communicate()` after `kill()`), while a reader thread waits in
  `_readerthread`. Any Windows command whose descendant keeps the pipe open hangs its caller the
  same way.
- On 2026-11-01 the owner stated that a repository with cross-platform requirements should not use
  PowerShell or another platform-bound shell.
- pywin32 312 is already in the locked closure on Windows (through `mcp`), with wheels for CPython
  3.12 to 3.14 on x86, x64 and ARM64.

## What Changes

- pywin32 becomes a direct Windows dependency, declared with its environment marker, and the
  dependency declaration check parses requirements with `packaging`, so it admits the marker and
  still refuses anything but one lower bound.
- The hosted `supply_image` build is admitted from a proposal ref as well as `dev`, so the lane
  binds a GitLab supply image built from its own lock change before it lands, and GitLab never
  refuses the landed head.
- Trust-anchor observation and protection call `GetNamedSecurityInfo` and `SetNamedSecurityInfo` in
  process. The decision is unchanged: the owner must be the current identity and only it, SYSTEM and
  Administrators may hold write-like authority; a null DACL, an unreadable descriptor or an entry
  ETHOS cannot classify is never protected.
- Process observation on Windows reads `Win32_Process.CommandLine` through WMI in process, on a
  bounded worker thread.
- On Windows a command's stderr is captured in a file, as its stdout already is, so a timeout's
  cleanup never waits for a descendant to close a pipe.
- `windows_powershell`, its unavailable diagnostic, the UTF-8 preamble and the acceptance
  environment's PowerShell directories are deleted with their last callers; Windows-only tests that
  plant a foreign ACL entry use `icacls`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: Windows trust anchors use the native security API in process.
- `runtime-activation`: Windows process observation uses WMI in process within a bound.
- `quality`: a Windows timeout returns within its cleanup bound, and native Windows observation no
  longer starts PowerShell.

## Impact

`pyproject.toml`, `uv.lock` and therefore the GitLab supply image binding, `.config/checks/deptry`,
`tools/ci/dependency_hygiene.py`, `src/ethos/adapters/process.py`,
`src/ethos/adapters/repo/trust_anchor/filesystem.py`,
`src/ethos/adapters/repo/runtime/retirement.py`, `tools/ci/delivery/acceptance/host_environment.py`,
the host proof's case selection in `tools/ci/delivery/pipeline.py`, their tests and the three
specifications. Windows behavior is proven only by hosted Windows runs. A paradigm rule that keeps
platform shells out of every governed repository's product code is a separate Change, because it
needs an adopter inventory first.
