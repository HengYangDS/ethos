# Design

`retire-unbound` is a small maintainer surface over repository truth. It reads
the existing workspace status coordination model, selects only a ref already
reported under `unbound_work_lane_refs`, and refuses anything outside the
configured Work Lane role.

Apply mode fails closed unless all of these are true:

- the branch exists and matches the configured Work Lane role;
- the branch is unbound, not linked to a worktree;
- `--expect-head` equals the current ref head;
- `--reason` is non-empty;
- `--authorize` is present.

Deletion uses `git update-ref -d refs/heads/<branch> <expect-head>`, making the
mutation a HEAD-bound ref transaction. If another agent moves the ref between
inspection and mutation, Git refuses the deletion.

This keeps `几动于微`: residue is visible before disorder grows. It keeps
`度协畛域`: landed linked lanes use `retire-landed`; unbound local residue refs
use `retire-unbound`; remote publication and deletion stay outside this local
command.
