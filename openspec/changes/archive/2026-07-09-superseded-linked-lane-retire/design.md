# Design

`retire-superseded` is a small mutation surface over existing repository facts:
Git branch/worktree state, local Work Lane lease, `ETHOS_ACTOR`, and the current
accepted branch head. It does not create a new truth store and does not assert
semantic correctness by itself.

Apply mode fails closed unless all of these are true:

- `--branch` exists and matches the configured Work Lane role;
- the Work Lane is linked to a worktree;
- the linked worktree is clean;
- the branch is not already merged into accepted root;
- the active lease owner matches `ETHOS_ACTOR`;
- `--expect-head` equals the current Work Lane head;
- `--absorbed-by` equals the current accepted root head;
- `--reason` is non-empty;
- `--authorize` is present.

Deletion first deletes `refs/heads/<branch>` with a head-bound
`git update-ref -d` transaction, then removes the previously verified-clean linked
worktree. If the branch moves between inspection and mutation, Git refuses the
ref deletion and leaves the worktree in place. If worktree removal fails after a
successful ref deletion, ETHOS attempts to restore the branch ref at the same
expected head and reports rollback stderr if that restoration also fails.

The command is intentionally not a semantic verifier. The absorption judgment
comes from higher-authority review, evidence, and accepted-root state; the
command only makes that cleanup auditable and fail-closed.
