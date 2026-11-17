# Proposal

## Why

Appendix A.7 of the archived `rc-plan` design states the rule (its second sentence): "The Git
configuration overlay reaches local Git only, with only the keys that `system/surfaces.toml`
declares, starting with exact-path `safe.directory`; network Git and signing get none, other keys
are dropped and named in `summary.environment`, and other children get no overlay, no
`VIRTUAL_ENV` and closed stdin." The Change `environment-entry` (A7) handed that sentence to the
row `gate-environment` (its Decision 8). `gate-environment`, the row's first slice in
0.2.0-beta.13, names the overlay's keys in a result and hands the declaration to this Change
(its Decision 10); `gate-child-environment` withholds the overlay from gate children.

What is left is local Git. The Git adapter gives local Git every key of the overlay and refuses
a wildcard `safe.directory`; network Git gets none. A spike of 2026-11-17 showed that the
overlay's count reaches both kinds of gate child as well. Which keys and values local Git admits
changes the environment of every Git call of the product and of its suite: the suite's own
overlay carries `core.fsmonitor`, `maintenance.auto` and, for each test, `init.templateDir`, and
one of those keys can name a program. The adapter's module holds 490 of its 500 effective lines,
so the declaration needs that module split first.

## What Changes

Candidates for this row's design, none decided:

- `system/surfaces.toml` declares the keys that local Git admits, starting with an exact-path
  `safe.directory`, and a rule for the values of a key that can name a program.
- A key that is not declared is dropped, and the result names it in `summary.environment`
  beside the keys that `gate-environment` already names; or it is named for one release before
  it is dropped.
- Signing receives no overlay.
- How the suite keeps its isolation: its three keys are declared, or the suite sets them by
  another carrier.

Estimated at 40 product and 80 test line-equivalents, without a spike and before the split.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

`src/ethos/adapters/repo/git.py`, `system/surfaces.toml`, the suite's Git isolation and every
result that names a dropped key.

Owner: the release lead. Next action: decide which keys and values the declaration admits, with
the suite's three keys as its first cases. Read again: at the cut of 0.2.0-beta.14.
