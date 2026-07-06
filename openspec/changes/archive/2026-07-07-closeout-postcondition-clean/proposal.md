# Closeout Postcondition Clean

## Problem

Closeout worktree synchronization now resets the accepted checkout to the
candidate head, but `accepted_validated` still depended on the sync command
succeeding rather than on the final accepted checkout state being clean.

A related lifecycle gap existed for OpenSpec carriers: reader/audit surfaces could
see completed-unarchived or promoted active carriers, but mutation admission did
not itself reject those carriers. That left a bypass path for adapter-level callers.

## Change

Make an empty accepted-root `git status --short` a postcondition for
`accepted_validated`. If the checkout remains dirty after sync, closeout reports
`accepted_worktree_dirty_after_sync`.

Also make OpenSpec carrier legality a mutation-admission precondition: completed
active Work Lane changes block land, and any active carrier in candidate or
accepted-root truth blocks closeout.
