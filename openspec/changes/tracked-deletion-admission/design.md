# Design

## Context

See [proposal.md](proposal.md). `check_write_paths` checks each requested path once with
`_check_path`, then re-checks the ignored and received ones. With index effects from staged
admission, `_check_path` takes `created` from the effect; without them it sets
`created = not present`, so any absent path is a creation and `paradigm_path_gaps` applies to it.

## Goals / Non-Goals

**Goals:**

- Prewrite admits the deletion of a tracked path whose location the paradigm rejects.
- A new path at such a location stays refused.

**Non-Goals:**

- Changing staged admission, which already reads deletions from the index.
- Changing which locations the paradigm rejects, or the repository audit of tracked carriers.

## Decisions

- **A path absent from the worktree is a deletion when the index or HEAD tracks it.** One
  `git ls-files` read of the index and one `git ls-tree` read of HEAD, with literal pathspecs, cover
  the absent paths of a request; a path that either lists is not created by its write. This covers
  an unstaged deletion, which the index still tracks, and a staged one, which only HEAD tracks.
- **The deletion re-check reuses the existing second pass.** Deleted paths join the ignored and
  received paths that `check_write_paths` already re-checks, and they leave the creations from
  which received paths are derived.
- **An unreadable index fails closed.** A failed index read raises, and `check_write_paths` reports
  `prewrite_tracked_observation_unavailable`, as it reports an unreadable ignore state. A missing
  HEAD, as in a repository without commits, only leaves HEAD's contribution empty.

## Risks / Trade-offs

- [One more Git read per request with absent paths] → Requests without absent paths make no read.
