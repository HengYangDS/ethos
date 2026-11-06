# Design

## Context

See [proposal.md](proposal.md). `changelog_errors` validates the entry against the release target,
and the release assembler publishes the entry as the release notes.

## Goals / Non-Goals

Goals:

- The notes tell adopters what changed, which upgrades were qualified, and what remains open.

Non-goals:

- Repeating the Changes' designs. The entry names behavior, not implementation.

## Decisions

- **One entry for the two lanes.** The fixes from `20261105-release-path` and this lane ship
  together, because none of them has been released yet.
- **Known defects stay visible.** The npm bundle's advisories are still unfixed upstream, so the
  entry lists them again, as beta.3's did.

## Risks / Trade-offs

- The entry's dates and journey claims must match the release run. The release readback checks
  the published notes against the entry.
