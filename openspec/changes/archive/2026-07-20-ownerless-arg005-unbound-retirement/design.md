## Context

`work/arg005-coverage-edges-20260719` is an unbound, lease-free ref whose exact
head is already in accepted history. It has no linked worktree and its one-file
parity delta has been superseded by current accepted parity evidence. The
native exceptional unbound command already supplies the guarded effect, but it
requires a target-specific accepted Claim and Chronicle.

## Decision

Use one current-base authority carrier containing only the target-specific plan,
Claim, Chronicle, and OpenSpec delta. After normal proof, candidate land, and
local closeout, the native command must re-observe exact target controls and
compare-and-delete that one ref. The carrier then retires normally.

## Risk controls

- A changed target head, relation, worktree binding, lease state, Claim,
  Chronicle, or protected ref blocks the effect.
- The target is clean and unbound; no preservation package or lease recovery
  is needed.
- The sibling `work/skill-scripts-ruff-20260719` is expressly excluded because
  it is dirty and linked despite sharing the source head.
- No raw Git/SQLite deletion, remote action, or hosted-state claim is admitted.
