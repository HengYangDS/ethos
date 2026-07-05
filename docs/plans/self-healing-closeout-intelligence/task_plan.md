---
subject: ethos:self-healing-closeout-intelligence-plan
role: plan
state: active
relations: supports: self-healing closeout intelligence lane
---

# Self-healing closeout intelligence plan

## Status:

Active work-lane planning document.

## Purpose:

Keep the self-healing closeout intelligence batch recoverable and auditable.

## See also:

- `docs/plans/self-healing-closeout-intelligence/task_plan.md`
- `docs/plans/self-healing-closeout-intelligence/findings.md`
- `docs/plans/self-healing-closeout-intelligence/progress.md`


## Acceptance

This batch is done when ETHOS can surface practical next actions for common closeout failures without weakening existing gates:

1. closeout / land failures expose residue-aware guidance when Git leaves accepted-root or work-lane state dirty;
2. workspace status reports dirty-state provenance with enough structure to distinguish tracked edits, untracked files, deleted files, and conflicted/index states;
3. lane overlap reports identify when a temporary/rebased lane overlaps a legitimate leased lane and recommend moving the legitimate lane to the verified head instead of landing the temporary lane;
4. coverage hard-floor policy records the current evidence-bound hard gate and keeps aspiration explicit instead of implicit;
5. reference-transaction regression covers both raw accepted-ref bypass blocking and official closeout admission.

## Constraints

- Do not touch `packages/ethos/src/ethos/domain/land.py` or parity evidence unless required; `work/parity-freshness-tree` owned by `ultra` currently overlaps those files.
- Keep names plain; no new obscure philosophical subsystem names.
- Prefer small diagnostics and tests over broad architecture churn.
- Preserve existing gates; do not add bypasses.

## Work items

1. Add dirty provenance to `workspace_status` and tests.
2. Add closeout/land failure guidance for `accepted_update_failed`, `work_lane_dirty`, `candidate_base_stale`, and scope overlap.
3. Add lane overlap migration recommendation in coordination/status payloads.
4. Add coverage policy record and architecture test binding the current hard and aspirational floors.
5. Add focused ref-transaction official closeout regression.
6. Validate with focused tests, `ethos status`, `ethos report`, `ethos prove`, land/closeout/publish.
