# Design

## Context

See [proposal.md](proposal.md). `resolve_archive_head` walks from an archived head through refresh
and repair edges. It collects every commit that has the archive's tree and is an ancestor of the
current head, then selects the nearest one.

## Goals / Non-Goals

Goals:

- A refreshed lane still finds an archive that the refresh rewrote.
- An archive that current history already contains resolves at its own ancestry distance.

Non-goals:

- Any change to refresh or repair edge validation, or to how the nearest archive is selected.

## Decisions

- **The walk stops at current history.** A commit that is an ancestor of the current head is the
  archive that current history preserves. A refresh edge from it can only move a branch past it,
  and it rewrites nothing that commit holds, so following that edge adds a stale candidate.
- **The direct case is unchanged.** An archived head that is itself an ancestor already returns
  early.

## Risks / Trade-offs

- A history that contains both a rewritten archive commit and its own predecessor would resolve to
  the nearer one, as today. That cannot happen through one refresh, which replaces the
  predecessor.
