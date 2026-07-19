## Context

`ethos lane retire unbound` already implements a narrow, accepted-policy-bound,
compare-and-delete transition for one exact accepted-ancestor ref. The present
lease-free residue meets the structural preconditions but lacks accepted,
target-specific Chronicle and Claim bindings. Existing historical Chronicles
describe its original work, not a later exceptional effect.

## Goals / Non-Goals

**Goals:**

- Preserve exact branch/head identity for the target.
- Make absorption evidence explicit without asserting source-tree identity.
- Require one later native command and one receipt for the source ref.

**Non-Goals:**

- No batch delete route, raw Git or state deletion, lease takeover, force
  worktree removal, remote push, hosted CI observation, or action on diverged
  and dirty residues.

## Decisions

1. **Use one Claim/Chronicle pair.** The command accepts one branch, and this
   carrier deliberately remains congruent with that one-target authority.
2. **Use historical freshness for evidence claims.** The target facts are
   immutable source identities; later native effects still require current
   re-observation and do not reuse this carrier as freshness proof.
3. **Retire only after carrier acceptance.** The OpenSpec carrier records policy
   evidence; proof, candidate land, accepted closeout, and native receipts are
   separate lifecycle transitions.

## Risks / Trade-offs

- **The target changes before apply** → native exact-head admission blocks the
  target and preserves the ref.
- **A Claim or Chronicle drifts after acceptance** → byte-identity admission
  blocks the target.
- **Candidate advances during carrier work** → refresh the owned lane and redo
  parity and HEAD-bound proof; never overwrite candidate.
