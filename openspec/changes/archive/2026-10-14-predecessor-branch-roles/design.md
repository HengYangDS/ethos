## Context

Branch roles govern which refs ETHOS protects and how they move. Accepted closeout reads them from the incumbent accepted head, so a candidate cannot change the topology that admits its own transition. `strict_branch_role_policy_from_text` requires all seven fields. Its opt-in recognized one predecessor generation, the six-field table without `canonical_sibling_worktrees`. Adopters that joined before `release_mirror` was declared hold a five-field table, and the lenient reader has always interpreted it as an independent release mirror without canonical sibling worktrees.

## Decisions

1. Read predecessor generations with their historical defaults instead of promoting the candidate's table. The governance contract keeps accepted controls on incumbent provenance and lets unavailable incumbent provenance defer rather than trust candidate controls. A promotion would let a candidate choose `release_mirror` for the transition that admits it.
2. Recognize exactly the two historical shapes. A table that lacks any other field, or lacks `release_mirror` while declaring `canonical_sibling_worktrees`, is not a historical generation and stays unavailable.
3. Rename the opt-in to `allow_predecessor_defaults`, so the name states what it admits. Both callers read incumbent heads only.
4. Fail an unclassifiable candidate-integration ref move in `_ref_operation`, the single place that derives intent operations. The reason names the ref, so an adopter can see that its declared roles do not cover the move.
