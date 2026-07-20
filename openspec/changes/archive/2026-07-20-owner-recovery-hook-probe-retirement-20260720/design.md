## Context

`work/owner-recovery-hook-probe-20260720` is unbound and lease-free; its exact
head is already in accepted history. It has no linked worktree and its one-file
parity delta is historical rather than current evidence. Later accepted parity
projections supersede that payload while the source commit remains retained in
Git history. The native exceptional command supplies the guarded effect but
requires a target-specific accepted Claim and Chronicle.

## Decision

Use one current-base authority carrier containing only the target-specific plan,
Claim, Chronicle, and OpenSpec delta. After normal proof, candidate land, and
local closeout, the native command must re-observe exact target controls and
compare-and-delete that one ref. The carrier then retires normally.

## Risk controls

- A changed target head, relation, worktree binding, lease state, Claim,
  Chronicle, or protected ref blocks the effect.
- The target is clean and unbound; no preservation package or lease recovery is
  needed.
- Historical provenance is retained, but stale parity evidence is not promoted
  as a current proof.
- No raw Git or SQLite deletion, remote action, or hosted-state claim is
  admitted.
