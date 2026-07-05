## Context

The official carrier is this OpenSpec change. The product boundary is the
workspace-status command JSON schema. Git refs remain substrate truth; ETHOS
only projects them into inspectable coordination facts.

## Design

`branch_bindings` remains the branch-level truth projection. `coordination` now
adds `unbound_work_lane_refs` as a focused read model for the same facts:
branch, head, claim binding, relation to accepted truth, and next action.

This keeps the existing count and advisory gap for compatibility while making
the hidden residue auditable. Relation is computed with Git ancestry checks,
not by branch name or stale memory.

## Alternatives

- Delete old refs immediately: rejected because deletion is a mutation decision
  that needs ownership or supersession evidence.
- Add a new truth store: rejected because Git refs already own the facts.
- Keep only a count: rejected because it hides the subject that needs judgment.

## Proof Strategy

- Unit and CLI tests assert unbound ref objects in status output.
- Workspace-status schema validates the new object shape.
- Live status in this lane shows `work/dissolve-cache-table` as
  `diverged_from_accepted` with inspection guidance.
- Claims and OpenSpec lifecycle checks bind the change before land.
