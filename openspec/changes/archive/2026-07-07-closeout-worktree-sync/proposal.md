# Closeout Worktree Sync

## Problem

`ethos land --closeout --apply` could return `accepted_validated` after advancing
the accepted ref while leaving the accepted checkout's index/worktree on the
previous tree.

## Change

After the accepted-ref compare-and-swap succeeds, synchronize the accepted
checkout with a checked `git reset --hard <candidate-head>` under the sanctioned
closeout environment. Dirty accepted roots are already blocked before closeout.
