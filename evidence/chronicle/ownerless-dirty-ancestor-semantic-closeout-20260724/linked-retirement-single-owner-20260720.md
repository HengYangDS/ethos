---
subject: ethos:ownerless-dirty-ancestor-semantic-closeout-20260724:linked-retirement-single-owner-20260720
role: evidence
state: active
event: lane_resolution/preserve-retire
target_branch: work/linked-retirement-single-owner-20260720
target_head: 66240184e924e965ff4dafa8b9cf3688b56b0a28
claim: ownerless-dirty-linked-retirement-single-owner-20260724
---

# Dirty ownerless closeout: linked retirement single owner

## Exact observation

The source is a linked, dirty, missing-lease, claim-free accepted ancestor at
`66240184e924e965ff4dafa8b9cf3688b56b0a28`. Its staged-plus-working binary diff
from HEAD is 63,529 bytes with SHA-256
`6dd6465217d807c8ce7011ab2611f7001500bb3e94bf54b94a45eb94aca19955`.
It touches eleven paths, including an `MM` retirement core, deletion of the old
`lane_retirement/landed` package, linked and superseded retirement tests, module
layout policy, and the Ruff ratchet. The package must retain both index and
working-tree state; the one-line unstaged change must not be lost.

## Semantic absorption and supersession

The patch's durable intent is one linked-retirement owner in
`lane_retirement/core.py`, removal of the separate `landed` package, and an
independent unbound boundary. Accepted `dev` has exactly that topology: the
`landed` package is absent, the CLI no longer imports it, and
`test_lane_retirement_has_one_linked_owner_and_independent_unbound_boundary`
is present and passes. Two dirty test blobs are byte-identical to accepted
history, and the accepted focused retirement suite passed 89 tests in total.

The remaining dirty source and test blobs are an incomplete historical
implementation and are not byte-replay candidates. Accepted code has continued
through owner binding, declarative lifecycle, and closeout hardening. Replaying
the stale 420-addition/541-deletion patch would regress those later controls.
The semantic intent is therefore absorbed while the concrete half-refactor is
explicitly superseded.

## Bound decision

After this carrier is accepted, native resolution may select only
`work/linked-retirement-single-owner-20260720` with disposition
`preserve-retire`. It must preserve the full index and working delta in a
verified package before removing the source ref and worktree. The package is a
recovery record for historical audit, not permission to replay stale code.
