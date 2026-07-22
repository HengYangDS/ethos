# Declarative lifecycle matrix retirement recovery — 2026-07-22

event: lane_retire/unbound_exceptional
target_branch: work/declarative-lifecycle-matrix-successor-20260720
target_head: 489a52d96b9abf49bfaa76be334b4bb72fdd984f
target_claim: declarative-lifecycle-matrix-20260720

## Fact

- Local `main`, `dev`, and `candidate/dev` are equal to the target head.
- The native landed-retirement attempt removed the clean linked worktree, then
  preserved the exact branch and owned Lease after the reference hook rejected
  Git's `verify` projection as an apparent accepted-branch deletion.
- The repair replaces that ambiguous `verify` with an atomic same-value update
  CAS and proves the real armed-hook retirement path.
- This Chronicle authorizes only the exact unbound continuation named above; it
  does not authorize any foreign lane, remote mutation, or history rewrite.
