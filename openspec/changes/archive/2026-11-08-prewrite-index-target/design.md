# Design

## Context

See [proposal](proposal.md) and [governance delta](specs/repository-governance/spec.md).
The existing staged admission owner already evaluates a staged tree against
current lane authority, official intent and artifact ownership. An index patch
must reuse that owner rather than substitute working-file bytes.

The predecessor source remains in Git. Its local results do not replace the
reviewed contract or released-runtime acceptance.

## Goals / Non-Goals

**Goals:** exact index-patch preflight, explicit mutable-prestate binding,
preservation of mixed content, and one staged admission interpretation.

**Non-goals:** execute staging, retain a permission object, change hooks,
change root catalog or result routing, redesign the paradigm, or install a
runtime. The catalog-root contribution is a base dependency, not this seam.

## Decisions

### Extend the existing request

Expose `--target worktree|index` on `lane prewrite --patch <file>`. Worktree
remains the default. Index mode requires the exact patch and the normal
editor-root, lane, actor and Lease checks. The request binds all native effect
paths; a rename or copy includes its source and destination.

### Native check, isolated prospective tree

Capture the real index path and exact bytes, HEAD and observed index tree.
Use a disposable index copied from that prestate and an isolated object
directory with the repository object store as a read-only alternate. Run
`git apply --cached --check` against that captured index before applying the
same patch to the disposable index to obtain the prospective staged tree.

Pass the candidate environment through the explicit `index_env` parameter to
the existing prospective staged readers, including staged OpenSpec observations.
Only scratch preparation writes candidate index/object state; staged readers
receive that environment, but repository Git writes, ref and lifecycle effects
never do. A staged reader without candidate custody fails closed rather than
substituting working-file bytes. Do not create another policy interpretation.
Preview has no real staging, working-file, ref, shared-object-store or Lease
effect. Candidate objects disappear with the temporary directory after every
result; permitting a ref write in that scope could leave a dangling ref.

A split index depends on its `link` extension and `sharedindex.*`, which a lone
index copy cannot carry. Refuse it as unknown with
`prewrite_index_split_index_unavailable`. A present real `index.lock` likewise
refuses as unknown with `prewrite_index_locked`. Sparse indexes use native
`git apply --cached --check` and cached apply on the disposable copy; successful
native handling is supported without expanding or changing the real index.
Other unreadable or conflicted index observations remain unavailable.

### Exact compare-and-swap binding, not a staging executor

The expected mutable state binds the observed index tree, exact index preimage
digest, HEAD, patch digest, paths and current Lease observation separately from
the prospective tree. After evaluation, reobserve the real prestate and refuse
its drift with a dedicated stale-index gap. Unreadable required state is unknown.
Do not restore a concurrent writer's index or working content.

Prewrite does not perform the swap: its result is a non-reusable decision, not
a permit. ETHOS exposes the expected real index tree and preimage digest for
the caller; it does not execute at the caller's later native `git apply --cached`
boundary or claim to enforce a CAS there. The existing pre-commit staged
admission re-admits the actual staged content when the caller commits.

### Keep one implementation owner

Extend the existing prewrite/staged admission owner and its lane CLI flag.
Small internal preparation helpers do not select policy or execute real staging.
No root catalog, hook, paradigm, adapter controller or durable state is added
or modified by this implementation. Incidental gaps outside the seam remain
with their existing owners rather than expanding this Change.

### Alternatives

Whole-file staging consumes unrelated bytes and is rejected. Worktree patch
preflight evaluates the wrong preimage when index and worktree differ. A second
staging command duplicates the existing owner and is rejected. Native cached
patch checking plus isolated staged-tree admission preserves the required
behavior with the existing executor and policy boundaries.

## Risks / Trade-offs

- Concurrent index writers invalidate the observation: exact prestate
  comparison blocks without undoing their effects.
- A captured tree is content identity, not byte-exact index identity: bind
  both the tree and preimage digest instead of substituting one for the other.
- Candidate readers can lose object custody: use one isolated environment
  through the existing readers; never publish scratch objects to mask a gap.
- Missing, conflicted or unreadable indexes remain unknown or blocked, not
  inferred from working files.

## Migration Plan

Exercise RED against the
incumbent for a valid index-only patch, mixed staged/unstaged preservation and
stale index rejection; then qualify GREEN through the extended public command
and directly affected sibling consumers. Use one fixture repository and
parametrized journeys/refusals, aiming for at most 250 readable test lines,
without `noqa` or a file exceeding 500 lines.

Before proof, refresh this lane after `record-retirement-apply` lands without
claiming that base's work as this Change. Notify the owner before any land or
closeout, use the host proof slot, and keep signing and independent gates.
After release, the owning adopter agent reruns its exact stage-preview patch
and checks unchanged source/index state as adopter follow-up, not a task this
Change can close. Alphasim and di-effect are deferred families: candidate and
released-runtime replays stay read-only. Local candidate diagnostics do not
replace release acceptance. Runtime binding and rollback require separate
authorization.
