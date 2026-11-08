# Design

## Context

See [proposal](proposal.md). Public prewrite currently materializes worktree
patches; the hook already admits exact staged trees and fences HEAD/tree drift.
A partial staging request must not substitute working bytes for index bytes.

## Goals / Non-Goals

**Goals:** reuse current authority, path-origin, official intent and staged
artifact admission for an exact prospective index; preserve unrelated staging
and worktree content; keep prestate and prospective identity distinct.

**Non-Goals:** execute staging, persist a permit, change hook policy, manage
adopter indexes, or weaken signing and proof requirements.

## Decisions

### Explicit target, unchanged default

Expose `--target worktree|index` on `lane prewrite`. An index request requires
an exact text patch whose native paths equal the requested paths. Requiring a
patch avoids treating path-only permission as authorization for arbitrary
staging. A rename or copy binds both native source and destination identities,
not only the postimage path. Whole-file staging and a separate staging command
are rejected.

Index path identity is lexical within the repository, matching the staged
observer rather than following unrelated working-tree symlinks. Outside-root
paths and parent traversal remain invalid.

### Disposable index, shared admission

Copy the exact real index into an owned temporary directory. Apply the patch
with native `git apply --cached`, never `git add` or worktree materialization.
Read the resulting tree through existing staged artifact admission and ordinary
prewrite authority/scope checks. Existing staged content remains in that tree;
no new policy implementation is added. Reuse native object-directory isolation
with the repository store as a read-only alternate. Candidate readers receive
the same explicit environment, including staged-reference and incoming-Change
observation. The real index, object store, refs, worktree and Lease are not
effects of this command. The prospective tree names content but is not retained
after the temporary index and objects retire.

### Fence the real prestate separately

Capture real index path, exact bytes/digest and HEAD before preparation. Recheck
fresh real index bytes and HEAD after all admission owners finish, separately
from the existing prospective-tree fence. Report target, patch digest, index
preimage digest and prospective tree in the existing exact-request decision.
Any drift blocks; unreadable state is unknown. The decision remains non-reusable
and requires recheck at the actual Git effect. Temporary state is removed on
success, refusal and exceptions.

### Reobserve authority at the shared staged boundary

After material-scope evaluation, staged admission reobserves the effective
branch, invocation actor and current Lease. A changed valid Lease or invalid
current authority cannot inherit an earlier pass. The effective branch retains
the existing owned-rebase interpretation; a detached rebase HEAD is not a new
lane identity. This fence belongs to staged admission, so index previews and
hook consumers use the same authority owner.

## Risks / Trade-offs

- Concurrent writers can invalidate preparation → compare exact real prestate
  after admission; do not overwrite or restore another writer's changes.
- Prospective intent differs from worktree intent → reuse the staged-tree
  OpenSpec resolver rather than silently substituting working artifacts.
- A reader without the candidate environment cannot resolve isolated objects →
  pass the same environment through every prospective-tree reader; do not publish
  candidate objects into the shared store to conceal a binding defect.
- Missing, unresolved or malformed index → fail closed without guessing a tree.

## Migration Plan

Add focused RED coverage for mixed staging, default-target refusal and stale
prestate; implement at the existing admission owner; qualify the public CLI and
actual adopter patches without real index effects. Prove and publish through
normal signed ETHOS delivery. Consumers select the index target only after a
qualified runtime provides it; rollback keeps the prior runtime and prestate.
