## Context

The campaign's first carrier has already been archived and locally closed on
the accepted root. The successor must make ordinary retirement safe before the
later recovery-package and deletion-admission slices can operate on any legacy
or dirty state. Git's normal `worktree remove` is a stronger final cleanliness
fence than a precomputed status observation; `--force` defeats that fence.

## Goals / Non-Goals

**Goals:**

- Keep routine retirement limited to an owned, clean, currently observed linked
  Work Lane.
- Reject stale ref/head/path observations before effects and preserve a newer
  or unobservable ref for later review.
- Treat unbound Work Lane refs as exceptional-deletion candidates, not routine
  cleanup.

**Non-Goals:**

- Do not create the sibling recovery-package v2 format in this slice.
- Do not decide, preserve, retire, move, prune, or repair any currently foreign
  lane.
- Do not claim remote publication, GitHub status, GitLab recovery, or hosted CI.

## Decisions

1. **Reobserve then remove worktree before ref deletion.** The implementation
   reads the selected checkout itself for branch ref, checked-out HEAD, and
   porcelain status against `--expect-head`; it calls non-forced `git worktree
   remove`; only then does a compare-and-delete ref update run from the still
   available controlling checkout. This makes a concurrent dirty write fail
   through Git and makes a concurrent ref change leave its ref intact.
2. **Retain explicit failure residue.** If the ref delete fails after worktree
   removal, the command returns a blocked partial-transition fact; it does not
   recreate a checkout or invent a recovery claim. A later audited decision can
   inspect that unbound residue.
3. **No ordinary unbound deletion.** The public unbound command becomes a
   fail-closed diagnostic. Later deletion-scope admission may introduce a
   separate, evidence-bound destructive mechanism.
4. **Campaign state follows independent proof.** The bootstrap is recorded as
   retired with its exact accepted/candidate head and tracked evidence; this
   slice alone becomes active.

## Risks / Trade-offs

- **An ordinary lane can become unbound after successful worktree removal but
  before ref deletion** → ETHOS reports the partial transition and does not
  delete or restore by inference; the ref remains inspectable.
- **Operators lose convenience deletion of stale unbound refs** → intentional;
  preservation/deletion evidence must exist first.
- **A race can occur after reobservation** → normal Git worktree removal is the
  final non-forced dirty-state fence and the ref delete is head-bound.

## Migration Plan

1. Land the adapter and specification change through the normal local ETHOS
   lane path.
2. Archive this carrier only after its checklist is complete.
3. Retire this clean owned implementation lane after local accepted-root
   closeout.
4. Start recovery-package v2 as the next independently admitted campaign step.
