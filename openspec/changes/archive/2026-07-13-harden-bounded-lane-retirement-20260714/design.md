## Context

Worktree status retains historical entries even when a path later disappears.
Landed retirement has a branch selector and owner/head checks, but currently
materializes retirement facts for all Work Lanes before applying that selector.
That expands a bounded request into an unsafe dependency on foreign filesystem
state.

## Goals / Non-Goals

**Goals:**

- Keep branch-scoped retirement operationally bounded to its selected lane.
- Preserve fail-closed semantics for a selected lane whose worktree path is
  unavailable.
- Avoid any direct or implicit foreign-lane mutation.

**Non-Goals:**

- Do not remove stale foreign worktrees, prune Git worktree records, or repair
  foreign leases.
- Do not make unavailable paths clean or retireable.
- Do not alter candidate/accepted closeout or publication semantics.

## Decisions

1. Filter the registered worktree list by `--branch` before invoking
   `_retirement_lane`; an unscoped report remains observational across all
   lanes.
2. Keep `has_changed_paths` as the single cleanliness seam, but catch an absent
   path at that seam and report it as changed/unavailable. This preserves the
   existing fail-closed meaning without duplicating Git status policy.
3. Add two focused tests: a selected owned lane retires despite a missing
   foreign lane, and a selected missing lane reports `work_lane_dirty` instead
   of throwing or deleting anything.

## Risks / Trade-offs

- **A stale foreign lane can remain visible** → intended; it stays advisory and
  owner-scoped rather than becoming a dependency of a selected action.
- **Unavailable selected lane is not automatically cleaned** → intended;
  callers receive a non-retireable state and must use separate recovery policy.
