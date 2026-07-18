# Superseded Linked Lane Retirement

## Problem

Multi-agent closeout can leave a clean linked Work Lane whose semantic truth has
already been reimplemented or fused into accepted root, while the lane branch
itself remains diverged and would regress repository truth if landed. Raw
worktree or branch deletion bypasses the Work Lane lifecycle, but `retire-landed`
only covers merged lanes and `retire-unbound` only covers refs without linked
worktrees.

## Change

Add `ethos lane retire-superseded` as the narrow governed cleanup path for this
third local residue state: a clean linked Work Lane, not merged into accepted
root, owner-bound, head-bound, reason-bound, and explicitly absorbed by the
current accepted head.

## Capabilities

- `ethos-repository`: subject=superseded-linked-work-lane-retirement; reuse=extend; change=add; facet:lifecycle=mutation; facet:surface=cli; facet:authority=source,test,openspec

## Out Of Scope

- No automatic semantic proof that a stale lane was absorbed.
- No deletion of dirty, unlinked, foreign, or already-merged lanes.
- No replacement for `ethos land`, `ethos lane retire-landed`, or
  `ethos lane retire-unbound`.
- No remote branch deletion.
