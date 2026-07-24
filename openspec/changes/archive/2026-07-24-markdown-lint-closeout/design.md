## Context

The Markdown owner script already runs in hosted CI and rejects the duplicate
blank line in the accepted closeout plan. The defect entered accepted history
before the GitHub public mirror caught up, so both a repository correction and
an explicit evidence boundary are required.

## Goals / Non-Goals

**Goals:**

- Restore Markdown conformance with the smallest possible content edit.
- State the existing owner-script failure boundary in the quality spec.
- Bind the corrective Work Lane to its own claim and Chronicle.

**Non-Goals:**

- Change markdownlint configuration, CI topology, or quality thresholds.
- Reinterpret the plan's ownerless-lane decisions.
- Reuse or take ownership of a foreign lane's claim.

## Decisions

1. Delete one redundant blank line instead of weakening MD012. The owner script
   remains the executable policy owner.
2. Modify the existing `Documentation Quality Profile` requirement only by
   adding a scenario for the already-enforced Markdown failure path. This makes
   the contract explicit without adding a second checker.
3. Use a dedicated claim and dated Chronicle. Existing ownerless-resolution and
   timeout claims have narrower, incompatible boundaries.

## Risks / Trade-offs

- **Risk:** A spec clarification could be mistaken for a new gate.
  **Mitigation:** The delta names the existing owner script and changes no
  configuration or command surface.
- **Risk:** Evidence can drift while files are edited.
  **Mitigation:** Recompute the Chronicle digest immediately before claim
  validation and commit.
- **Risk:** Old hosted runs remain red after the correction lands.
  **Mitigation:** Treat only fresh runs for the successor accepted HEAD as
  hosted evidence.

## Migration Plan

Archive the validated delta into the main quality spec, bind the lane claim,
run focused and full proof, then fast-forward accepted and both remotes. Roll
back by reverting the one-line document correction and the associated spec and
evidence carrier as one governed successor change.

## Open Questions

None.
