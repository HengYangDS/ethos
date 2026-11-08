# Design

## Context

Both sides of the merge appended entries at the same place, so Git cannot order them. The lane's
two Changes are archived, and the refresh's rebase strategy aborts on any conflict, so the native
merge strategy carries the resolution.

## Goals / Non-Goals

Goals: keep every entry of both sides verbatim, with the accepted side first.

Non-Goals: rewording an entry, reordering an existing one, or changing a requirement's text.

## Decisions

1. **The accepted side comes first.** The candidate's entries are already on `dev`, so they keep
   their place at the head of each list and the lane's entries follow them.
2. **The merge carries the resolution.** `ethos lane refresh-base --strategy merge` starts the
   merge, the two files are resolved under this Change's prewrite, and its `continue` mode records
   the merge commit, which the archive provenance follows like any refresh.

## Risks / Trade-offs

- Archiving a lane's Changes before a concurrent land forces a resolution Change; the order that
  avoids it is to refresh first and archive after.
