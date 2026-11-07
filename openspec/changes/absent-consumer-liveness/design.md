# Design

## Context

`retire_unused_installations` (`src/ethos/adapters/repo/runtime/materialization/host_retention.py`)
walks every recorded installation in the host store and asks each recorded consumer whether it
still needs it. `_consumer_state` answers `released` when the consumer's common directory does not
exist, `unknown` when its selectors cannot be read or its selection lock is held, and `needs` when
`CURRENT` or `ROLLBACK` names the installation. A `released` answer unlinks the consumer record, and
an installation that no answer keeps is removed. Path absence cannot tell a deleted repository from
an unmounted volume or a moved checkout, so it is not evidence of release.

## Goals / Non-Goals

Goals:

- Never delete an installation on the strength of a missing consumer path.
- Report the absent consumers, so the reason an installation stays is visible.

Non-Goals:

- The explicit, previewed release of an absent consumer; it belongs to store-retention (resolution
  R7(c)), which owns the byte budgets that make retention converge.
- Changing what `legacy_supply` plans for installations pinned before consumers were recorded.

## Decisions

1. **Absence is unknown liveness.** `_consumer_state` returns `unknown` for a consumer path that
   neither exists nor is a symbolic link. The record stays and the installation is kept, as for an
   unreadable selector or a held selection lock. Alternative: a grace period before an absent
   consumer counts as released; rejected, because no duration distinguishes an unmounted volume from
   a deleted repository.
2. **The report names absent consumers.** The result gains `absent`, the sorted consumer paths that
   were missing, beside `retired`, `retained` and `unrecorded`. Existing readers that ignore unknown
   keys are unaffected.

## Risks / Trade-offs

- Installations that only a deleted repository recorded now accumulate until the explicit release
  step lands with store-retention; each holds about 672 MB for beta.6. The report makes them visible.
