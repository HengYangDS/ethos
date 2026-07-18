# Design

The status read model remains the authority surface. A foreign Work Lane item classifies closeout disposition and also exposes a small residue state:

- `clean_or_none`: no dirty worktree delta requiring preservation.
- `unpreserved_worktree_delta`: the branch head is accepted, but the linked worktree still contains tracked or untracked deltas.

The next action is guidance only. It does not change `allowed_actions`, `forbidden_actions`, write policy, or retire policy.
