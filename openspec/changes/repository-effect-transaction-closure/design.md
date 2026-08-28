## Context

The terminal protocol is:

```text
fresh observe -> compile TransitionPlan -> effect-time recheck -> exact CAS
-> post-observe -> Attestation -> recover or compensate
```

The current implementation splits that protocol among `git_effects`,
`ref_intent`, the reference hook, Lease transition code, worktree effects, and
lifecycle-specific recovery modules. The most damaging overlap is ordinary
Work Lane ref movement: the hook's committed phase mutates `Lease.expected_head`
and `expected_tree`. A crash or hook failure after Git commits the ref therefore
creates valid-but-stale authority even though the ref itself is already the
current repository fact.

Git 2.55 subprocess evidence also establishes that `git merge --ff-only` and
`git checkout -b` can update the index and worktree before a prepared
reference-transaction rejection. The ref hook is atomic only for refs.

## Decision

### One local repository-effect owner

`execute_git_effect` is promoted into the sole local ref executor. It owns the
exact effect capability, effect-time observation, ref CAS, postcondition,
effect Attestation, and bounded compensation/recovery. Callers compile semantic
operations into the same `TransitionPlan`; they do not implement another ref
transaction.

The hook consumes the executor-issued exact intent in `prepared`, then observes
`committed` or `aborted`. It does not update Lease, persist an effect receipt, or
perform lifecycle recovery.

### Lease is authority, not a moving ref cache

A Lease generation binds lane incarnation, holder, expiry, and the selected
Commitment generation. Current branch HEAD and tree are fresh Git Facts bound
by each admission or TransitionPlan. Ordinary commits do not rewrite Lease
authority merely to mirror the current ref.

Transitions that actually change authority still replace the Lease generation:
start, rebind, succession, handoff, takeover, and retirement. They bind their
own exact pre/post coordinates in the TransitionPlan and Attestation.

### Raw Git fail-clean boundary

Protected integration mutation belongs to the ETHOS command plane. Defense-in-
depth hook rejection may compensate an already projected checkout only when:

- current HEAD is still the pre-effect HEAD;
- index tree exactly equals the rejected target commit tree;
- worktree exactly equals that index; and
- restoration post-observes the original HEAD tree.

Any non-exact overlay is not reconstructed or discarded. The hook reports the
blocked effect and leaves explicit recovery to the command plane.

## Deletion

- Delete committed-phase Lease advancement from the reference hook.
- Delete Lease HEAD/tree equality as current authoring authority after all
  consumers use fresh Git facts plus stable Lease/Commitment identity.
- Delete lifecycle-specific ref compensation/recovery once the unique executor
  owns equivalent semantics.
- Delete the unsupported `preparing`/`ORIG_HEAD` interception assumption.
