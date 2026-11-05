# Design

## Context

See [proposal.md](proposal.md).

- **The refusal.** `_supply_refusal` reads the selected mise's version. When a missing tool's lock
  entry references a dependency graph and the version is at least `_GRAPH_SAFE_MODE_REGRESSION`
  (2026.11.0), it names jdx/mise#15363 instead of `mise trust`.
- **The evidence for the bound.**
  - Upstream: the merge commits of jdx/mise#15392 (`98f2b511`) and #15401 (`16e4de8b`) are
    ancestors of `v2026.11.2`, which is 19 and 8 commits ahead of them and 0 behind.
  - Behaviour: fbee0c's isolated recheck of the official `mise-v2026.11.2-macos-arm64.tar.gz`,
    whose sha256 equals the release digest, passed every step with exit 0. It ran under separate
    mise configuration, data, cache and state directories, and installed nothing on the host.

## Goals / Non-Goals

Goals:

- The refusal names the regression only for the releases that have it.
- Its next action points to the fixed release, following the latest-stable preference.

Non-goals:

- Moving the host's or CI's mise pin. That waits for the host owner's acceptance and its own supply
  move.
- Changing what the refusal refuses.

## Decisions

- **A named fix bound.** `_GRAPH_SAFE_MODE_FIX = (2026, 11, 2)` sits beside the regression constant,
  and the condition becomes `regression <= version < fix`.
- **The next action names the fix.** The message becomes "select mise 2026.11.2 or later". An
  operator who cannot upgrade can still choose an earlier release, but the refusal recommends the
  current stable one.

## Risks / Trade-offs

- The behavioural recheck ran on macOS arm64 only. The fixes change platform-independent lock
  handling, and Linux and Windows hosted jobs exercise them when the CI pin moves. If a platform
  still showed the regression, its refusal would name trust or installation instead of the
  regression: less precise, but still a refusal.
