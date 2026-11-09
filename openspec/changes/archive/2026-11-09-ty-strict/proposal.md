# Proposal

## Why

The owner asked for every check to be tightened. ty runs at its default severities, which report
nothing, while `--error all` reports 394 findings at `9d0a8576d` with ty 0.0.99. Of these, 95 come
from five rules that the default leaves off. 59 of them are bare `dict` annotations. Others are
runtime guards whose annotations claim more than the parsed input holds, overriding methods
without `@override`, and casts between disjoint types, two of them Nox session doubles. A ty
upgrade cannot surface a new rule either, since the selection names none.

## What Changes

- `ty.toml` raises every rule to `error` and ignores four, each owned by a later Change of the
  gates program: `truthiness-test-of-none-union` (140 findings), `unsound-return-statement`
  (143), `unsound-assignment` (13) and `unsound-yield` (3).
- The 95 findings are fixed at their cause. The Nox sessions take a `Session` protocol that the
  real session satisfies, with one typed test double instead of casts.
- A planted case per raised rule class, and the ignored set pinned by equality, guard the
  selection.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The ty selection is ETHOS's own repository configuration. The shared static gate runs Ruff
alone, so no governed repository is affected; their type checking is a later shared obligation.

## Impact

- `.config/checks/ty/ty.toml`, the flagged product, tool and test-support files, and the ty gate's
  tests.
- No public behaviour changes.
