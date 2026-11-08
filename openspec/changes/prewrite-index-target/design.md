# Design

## Context

See [proposal](proposal.md) and [governance delta](specs/repository-governance/spec.md).
The existing staged admission owner already evaluates a staged tree against
current lane authority, official intent and artifact ownership. An index patch
must reuse that owner rather than substitute working-file bytes.

This is the review gate for the adopted seam. A predecessor source commit is
retained in Git; its implementation and prior test results do not establish
approval of this design. Code remains frozen until the owner reviews it.

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

Pass the same candidate environment to every existing staged owner that reads
the prospective tree, including staged OpenSpec observations. Do not create a
second interpretation of paths, intent or artifact ownership. Preview has no
real staging, working-file, ref, shared-object-store or Lease effect. Candidate
objects are removed with the owned temporary preparation after every result.

### Exact compare-and-swap binding, not a staging executor

The expected mutable state binds the observed index tree, exact index preimage
digest, HEAD, patch digest, paths and current Lease observation separately from
the prospective tree. After evaluation, reobserve the real prestate and refuse
its drift with a dedicated stale-index gap. Unreadable required state is unknown.
Do not restore a concurrent writer's index or working content.

Prewrite does not perform the swap: its result is a non-reusable decision, not
a permit. The actual staging consumer must reobserve the expected real index
prestate at the effect boundary and use its native index locking; a preview
cannot claim that a later mutation already passed compare-and-swap. Existing
Git-effect admission remains required and unchanged.

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

The owner reviews this design before code resumes. Exercise RED against the
incumbent for a valid index-only patch, mixed staged/unstaged preservation and
stale index rejection; then qualify GREEN through the extended public command
and directly affected sibling consumers.

Before proof, refresh this lane onto the accepted catalog-root base without
claiming that base's work as this Change. Notify the owner before any land or
closeout, use the host proof slot, and keep signing and independent gates.
Released-runtime acceptance reruns each adopter's exact stage-preview patch and
checks unchanged source/index state. Local candidate diagnostics do not replace
that acceptance. Runtime binding and rollback require separate authorization.
