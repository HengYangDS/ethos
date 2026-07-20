# Design

## Principle

Land readiness must be evidence-grounded. Dry-run readiness is still a reader
view, but it must not claim a Work Lane is ready to land when the exact HEAD has
no valid executed proof record.

## Minimal Mechanism

- Reuse the existing `executed_proof_record(root, head)` verifier through a small
  `proof_readiness_report` helper.
- Run the proof-readiness check only after earlier structural blockers are clear
  in work-lane `land --json`.
- Return `proof_not_proven` and the concrete command:
  `ethos prove --execute --expect-head <HEAD> --json`.

## Non-goals

- No new proof store.
- No change to apply-time proof enforcement.
- No hosted CI or remote publication claim.
- No accepted-root closeout semantic change in this lane.
