# Design

## Principle

A missing physical worktree path is not noise. It is repository coordination
state produced by the mismatch between Git's worktree registry and filesystem
reality. ETHOS should reveal that state while preserving boundaries: readers may
observe it, but only owner, handoff, or maintainer break-glass paths may mutate
or clean it.

## Minimal Mechanism

- Keep Git worktree metadata as the source fact.
- Extend the existing `worktree_binding` vocabulary with `missing`.
- Derive `missing` by comparing Git's registry path against filesystem reality.
- Keep candidate read-model bindings (`absent` when the configured candidate
  branch is absent, `unbound` when the branch exists without a worktree, and
  `missing` when registry metadata points at a missing path) distinct from
  actual worktree list entries, which remain physical `current`, `linked`, or
  `missing` bindings.
- When foreign-lane dirty paths would require entering a missing directory,
  return an empty dirty-path set and let `worktree_binding=missing` carry the
  disorder signal.
- Keep coordination advisory for accepted-root readers. A missing foreign path
  does not become proof that the current actor may retire or delete the lane.

## Kernel Binding

```text
Subject = Git repository and Work Lane branch
Commitment = role policy, lease, claim binding, and worktree registry fact
Change = foreign Work Lane lifecycle state
Evidence = status JSON, schema validation, focused tests
Claim = digest-bound evidence record
Chronicle = this archived carrier and dated evidence
```

## Alternatives

- Treat missing paths as dirty residue: rejected because no dirty paths are
  observable when the directory is gone; dirty residue would be a false claim.
- Hide or prune the worktree entry: rejected because hiding the signal would
  make concurrent cleanup drift invisible.
- Add a new missing-worktree store: rejected because Git registry plus status
  schema already owns the needed fact.
