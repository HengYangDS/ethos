## Why

Hosted verification of the exact candidate exposed two portability failures in
the shared execution boundary. On Windows, an installed wheel can run the
ETHOS CLI but immutable runtime materialization subsequently loses the package's
real `ethos` console entrypoint. On Linux, proof deliberately drops privileges,
but ETHOS Git observations discard the runner's exact repository trust and
commit identity, so the same checkout becomes unreadable after the identity
transition.

These are source/runtime portability defects, not provider-specific test
exceptions. They must be repaired at the two existing owners before the
candidate can become accepted.

## What Changes

- Preserve the installed distribution's real console-script entrypoint when
  constructing an immutable package-only Python runtime on every supported
  host, including Windows.
- Let repository Git observations retain only the explicitly supplied exact
  repository trust and deterministic commit identity while continuing to hide
  ambient global and system Git configuration.
- Add focused regressions for Windows package metadata/script discovery and
  Linux owner-different execution, then re-run both Hosted proof planes.
- Do not add platform fallbacks, per-test Git configuration, alternate runtime
  entrypoints, or a second environment abstraction.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: package-only immutable runtime materialization must preserve
  the installed ETHOS console entrypoint across supported hosts.
- `proof-hosts`: hosted execution under a reduced process identity must retain
  the exact repository trust and deterministic Git identity declared by the
  proof runner.

## Impact

The change is limited to immutable Python runtime materialization, the shared
Git subprocess boundary, the existing hosted Python test runner declaration,
focused package/runtime and Git regressions, and the two modified capability
specifications. It adds no dependency, compatibility carrier, provider-specific
exception, persistent state, or parallel command path.
