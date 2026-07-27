---
subject: ethos:unbound-retirement-native-lease-relinquish-20260719
role: plan
state: superseded
relations:
  implements: unbound-retirement-native-lease-relinquish-20260719
  extends: worktree-retirement-exceptional-unbound-v2-20260719
  superseded_by: ethos:terminal-governance-product-design
---

# Native Unbound-Retirement Lease Relinquishment — 2026-07-19

Status: superseded historical carrier. The terminal lifecycle exposes no
unbound-retirement command; the target remains an observation only.

Purpose: close one native-lifecycle deadlock without widening exceptional retirement:
when the exact current holder still owns the exact lease for an otherwise
accepted-ancestor unbound ref, the native command must be able to relinquish
that generation by its existing compare-and-swap and only then perform the
separate head-bound compare-and-delete ref transition.

## Boundary

The carrier changes only the native `lane retire unbound` transition, its
records, regression coverage, canonical documentation, and repository-governance
contract.  It does not accept, merge, refresh, or delete a historical source
lane; force-remove a worktree; use raw Git or SQLite deletion; mutate a remote;
or claim GitHub, GitLab, or hosted CI state.

## Transition Contract

1. Observe the exact source ref, accepted relation, Claim, Chronicle, protected
   refs, and lease binding.
2. Require any active lease to match `ETHOS_ACTOR`, lease ID, epoch, and target
   head exactly; foreign, malformed, stale, and mismatched state blocks.
3. Publish the no-clobber attempt record, including the exact lease generation.
4. Revoke only that observed generation through the existing lease CAS rooted in
   the accepted control store.
5. Re-observe all non-lease retirement bindings.  Drift leaves the source ref
   intact.
6. Compare-and-delete only the observed ref head, then require and record the
   ref, unbound entry, and lease to be absent while protected refs are unchanged.

## Acceptance and Follow-up

This carrier needs focused regressions, strict OpenSpec lifecycle, exact-HEAD
executed proof, native land, and accepted-root local closeout.  Only after that
separate acceptance may the holder invoke the one target-specific exceptional
retirement command.  Local acceptance and the resulting local receipt do not
constitute remote publication or hosted validation.

See also: [Runner and Mutation](../architecture/runner-and-mutation.md),
[Command Plane](../reference/command-plane.md), and the
[Repository Governance OpenSpec](../../openspec/specs/repository-governance/spec.md).
