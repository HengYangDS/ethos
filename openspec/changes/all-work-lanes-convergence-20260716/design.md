# Design

## Cohort and authority boundary

The program freezes the original 60 legacy refs as a sorted tracked inventory.
The governance carrier is recorded separately so its own lifecycle can be
closed last. The inventory records observations; it does not authorize effects.
The current user instruction is bounded to the frozen cohort and current
session. Every mutation still requires an exact branch, HEAD, observed dirty
state, worktree binding, lease/incarnation evidence, and the product's normal or
exceptional admission.

This avoids two unsafe interpretations: treating `work/*` as a permanent
wildcard authorization, or treating a branch name/ancestry result as proof that
a dirty or owner-unknown worktree can be deleted.

## Two-layer classification

The first layer is commit-graph and semantic intent:

- accepted landed residual;
- outdated or superseded;
- direct valid implementation; or
- semantic replay/reconciliation.

The second layer is the live worktree/lease overlay:

- clean or dirty;
- linked or unbound;
- normalized valid lease or missing/ambiguous lease; and
- active process observation.

A graph closeout candidate with a dirty overlay is therefore not a retirement
candidate. It is preservation and semantic-review work. The hosted-observation
lane demonstrates why both layers are required: its branch HEAD equals accepted
truth while its worktree contains a new uncommitted implementation.

## Implementation convergence

The 24 graph implementation refs are folded into 11 current-contract families.
The hosted-observation dirty overlay joins the hosted runtime/supply family.
Each family is implemented on the candidate-derived owned carrier by extracting
requirements and tests from all relevant lanes, proving the missing behavior
against current code, and adding only the minimal current implementation.
Stale carriers are never wholesale merged when their ownership, topology, or
contracts have since changed.

This approach keeps canonical current code above historical branch shape and
lets later accepted work supersede an old implementation without losing the
old lane's intended invariant.

## Valid leases and foreign lanes

A normalized lease protects the exact holder, lease ID, epoch, incarnation, and
HEAD. A foreign lane remains observe-only. Normal holder completion or
quiesced handoff is preferred. When it is unavailable, the original lane is
preserved read-only and its requirements are replayed in the owned carrier.
Absence of a visible process is evidence about activity, not authority.

## Missing leases and preservation

Missing or legacy lease state is not repaired by inventing a holder. The
accepted Chronicle binds the cohort policy, while each exceptional decision
binds one fresh target observation. Dirty lanes default to `preserve`; an
irreversible `preserve-retire` additionally requires break-glass and explicit
irreversible confirmation. Preservation must verify the bundle, tracked patch,
untracked archive when needed, manifest digest, and receipt before worktree/ref
removal.

Existing recovery packages remain outside ordinary housekeeping and are never
cleared by this program.

## Unbound refs

Three unbound refs are accepted ancestors and can use exact-head governed
unbound retirement after accepted judgment. The diverged unbound ref must first
be preserved and integrated. If the current CLI cannot create a recoverable
transition for that state, closeout remains explicitly blocked until the
product gap is implemented; raw deletion is not an acceptable substitute.

## Proof and lifecycle ordering

The ordered transitions are:

1. inventory and governance decision carrier;
2. strict completion and parity, followed by archive and stable-HEAD proof;
3. governance carrier land, accepted-root closeout, and self-retirement;
4. owned successor lanes for test-first semantic implementation;
5. successor strict completion, archive, parity, and HEAD-bound proof;
6. successor land and sanctioned accepted-root closeout;
7. exact cohort preservation and retirement; and
8. final successor-lane retirement.

The accepted governance Chronicle therefore exists before any exceptional
missing-lease or irreversible effect and removes a circular dependency between
implementation completion and resolution authority.

Candidate landing, accepted closeout, retirement, and remote publication are
separate facts. Remote publication remains deferred.

## Failure and rollback

Before candidate landing, rollback is a normal revert of the carrier commits.
After candidate landing but before accepted closeout, the candidate train is
re-audited and no raw reset is performed outside sanctioned recovery semantics.
After accepted closeout, legacy lane removal is separately receipt-bound; a
stale target observation blocks the effect and requires a new decision. A
preservation package is retained even if later integration is reverted.
