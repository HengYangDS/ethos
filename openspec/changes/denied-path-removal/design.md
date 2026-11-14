# Design

## Context

`check_write_paths` in `src/ethos/adapters/admission/paths.py` reports one decision for each
requested path. `ethos lane prewrite` calls it for a worktree request, and the pre-commit hook
calls it with the staged effects of the index. `_check_path` reads the placement from the
artifact topology and, when the placement is `deny`, reports the placement's gap. It computes
three facts about the effect before that line and does not use them there: `deleted` (the path is
absent from the worktree and tracked), the index effect `delete`, and `created`.

## Goals / Non-Goals

Goals:

- A tracked path under a denied placement can leave the repository through admission.
- An edit or a creation under a denied placement is refused as before.

Non-Goals:

- No change to the topology declaration, to its gaps or to the audit that reports a tracked path
  under a denied placement.
- No repair verb that plans such removals. The paradigm repair may gain one later; the owner of a
  repository decides what replaces the files.

## Decisions

1. **The effect is read before the placement refuses.** A denied placement refuses unless the
   request removes the path: `deleted` for a worktree request, the `delete` effect for an index
   request. The removal then takes the ordinary branch, so a protected role still refuses it with
   `protected_lane_tracked_write`. Alternative, not taken: a flag on the request that states the
   intent to delete. The guard already observes the effect, and a flag could disagree with it.
2. **A present path is an edit.** A worktree request for a path that still exists stays refused:
   the guard cannot tell an edit from a removal that has not happened. The file is removed first,
   or the request carries an index patch whose effect is the deletion.
3. **One rule for every denied placement.** The condition is on the placement's decision and not
   on a prefix, so denied generated homes and denied caches that a repository tracks can be
   removed the same way.
4. **The effect is observed in one helper.** `_observed_effect` returns whether the request
   leaves the path present, creates it or removes it, for a worktree request and for an index
   request. `_check_path` read those facts in three places; with the helper its pinned decision
   score falls from 19 to 16, where reading the removal in place raised it to 22.

## Risks / Trade-offs

- A removal under a denied placement is admitted without a Change-specific check beyond the
  ordinary scope checks that every tracked path gets. That is intended: the topology says the
  path does not belong there.
- A lane on a released runtime keeps refusing until it binds a release that carries this Change.
