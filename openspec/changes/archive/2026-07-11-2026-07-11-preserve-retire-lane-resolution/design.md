# Design

## Boundary

`preserve-retire` closes the unsafe gap between a non-destructive preservation
and a dirty-lane retirement that must otherwise fail closed. It is exceptional
only: an accepted Chronicle decision, exact observation recomputation,
`--break-glass`, and `--confirm-irreversible` are all required.

## Transition

1. Capture the lane branch as a Git bundle, its tracked delta as a binary patch,
   and its non-ignored untracked files as an archive.
2. Write a manifest binding each artifact to the decision and observation
   digests; verify the package before any destructive transition.
3. Delete only the observed ref and linked worktree. If worktree removal fails,
   restore the ref. The preservation package remains under the local
   lane-resolution artifact root for later reconciliation.

Plain `preserve` remains non-destructive and plain `retire` remains blocked for
dirty work. The new path creates no remote, hosted-CI, or identity authority.
