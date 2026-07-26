## Context

Accepted `dev`, `candidate/dev`, and `main` reached
`912d354e9c17c094b7c0cfab92800203fa6e0c33`. The original housekeeping carrier
was then retired. Native preservation and retirement of
`work/20260724-release-0-1-0a2` completed under decision
`lane-decision:17e26f03-0830-42f9-a311-f20d9f199701`; its verified package and
receipt remain in the stable records owner.

The first direct-retire decision for
`work/20260724-20260724-budget-contract-v2-changed-scope-source-admission` was
`lane-decision:6e57ce11-5723-4171-85a8-596452f118fa`. Decision dry-run, decision
write, and effect dry-run passed. Effect apply returned only
`lane_resolution_ownerless_chronicle_invalid` before reservation, package,
receipt, ref, or worktree mutation. Inventory truthfully records one pending
decision. The second budget predecessor has the same accepted Chronicle shape
and has not been subjected to a knowingly invalid effect attempt.

## Goals / Non-Goals

**Goals:**

- Make both budget direct-retire Chronicles satisfy the current effect-side
  accepted Chronicle contract.
- Preserve the failed decision and exact no-effect outcome without making it
  reusable after Chronicle repair.
- Reach the intended native accepted-ancestor boundary through new decisions
  only after successor acceptance.
- Keep the valid-owner budget lineage and retained release package untouched.

**Non-Goals:**

- No product parser change, compatibility alias, raw Git deletion, package
  clear, direct preserve-retire authorization, valid-owner takeover, remote
  operation, or whole-repository completion claim.

## Decisions

1. **Use a successor carrier rather than rewriting the archived carrier.** The
   accepted archive remains an exact record of the authority that produced the
   pending decision. This Change records the later observed contract failure
   and the bounded repair.

2. **Use new target Chronicles and new decisions.** A lane-resolution decision
   binds the Chronicle SHA-256. Changing accepted Chronicle bytes cannot make
   decision `lane-decision:6e57ce11-5723-4171-85a8-596452f118fa` valid. Each
   retry therefore receives a new Chronicle path, digest, and decision ID.

3. **Include the exact effect token as a standalone line.** Each new target
   Chronicle keeps `event: lane_resolution/retire`, exact `target_branch`, and
   exact `target_head` front matter, and also contains this line as ordinary
   document content:

   lane_resolution/retire

   This is the narrow current contract consumed by effect admission. It does
   not weaken the later accepted-ancestor check or authorize a changed target.

4. **Repair both identical authoring shapes, but reproduce only the observed
   failure.** The first decision supplies runtime evidence. The second target
   is corrected before any known-invalid apply; its branch, head, cleanliness,
   ownerless state, and descendant containment remain execution-time gates.

5. **Keep disposition change in a later accepted reconciliation.** Successful
   Chronicle admission is expected to expose
   `lane_resolution_ownerless_target_not_accepted_ancestor` for each diverged
   source. That no-effect result is not hidden or converted in this Change.

## Risks / Trade-offs

- **A target, owner, or descendant relation changes** -> Stop that target and
  leave its branch, worktree, decision records, and valid-owner lineage intact.
- **The repaired Chronicle still fails effect admission** -> Preserve the new
  pending decision and create no manual cleanup or alternate disposition.
- **Accepted-ancestor admission blocks as designed** -> Record the exact
  no-effect decisions in a later minimal preserve-retire reconciliation.
- **A retained package is mistaken for junk** -> Keep all lane-resolution
  packages outside generic filesystem housekeeping.

## Migration Plan

1. Add and validate this successor carrier, Claims, and Chronicles.
2. Archive through the official OpenSpec transition, refresh parity, execute
   exact-HEAD proof, land to candidate, and accepted-close.
3. Re-observe both exact budget targets and record new direct-retire decisions.
4. Require Chronicle admission to pass and preserve the expected
   accepted-ancestor no-effect results without source mutation.
5. Create the separate exact reconciliation carrier before any preserve-retire
   decision for those targets.

Rollback before accepted closeout is to discard only this owned successor lane.
After accepted closeout, a failed effect leaves the exact source and records
intact; raw ref or worktree manipulation is never a rollback path.

## Open Questions

None. Mutable lane, lease, registration, ancestry, and containment facts remain
execution-time predicates.
