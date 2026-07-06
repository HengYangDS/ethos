# Design

`update-ref` remains the compare-and-swap authority for the accepted ref. The
follow-up sync is a worktree projection of that same ref truth. `reset --keep`
can be ineffective after the ref move because HEAD already resolves to the new
commit while the worktree still contains the old tree. Checked `reset --hard` is
safe here because dirty accepted roots are blocked before closeout.
