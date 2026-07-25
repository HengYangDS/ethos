---
subject: ethos:self-healing-closeout-intelligence-plan
role: plan
state: archived
relations:
  archived_by: evidence/claims/plan-residue-closeout-20260709.toml
  summarized_by: evidence/chronicle/plan-residue-closeout-20260709/2026-07-09.md
---

# Self-healing closeout intelligence plan

## Status

Archived. This file is retained as the recovered planning record for the
completed `work/self-healing-closeout-intelligence` batch; it is not an active
work lane and does not authorize new mutation.

## Purpose

Preserve the acceptance criteria that guided the self-healing closeout
intelligence batch without leaving an active-plan residue in current ETHOS
planning surfaces.

## Outcome

The batch is closed in the accepted product state. Its mechanisms are now part
of the governed repository command plane and evidence model:

1. closeout / land failures expose residue-aware guidance when Git leaves
   accepted-root or work-lane state dirty;
2. workspace status reports dirty-state provenance for tracked edits,
   untracked files, deleted files, and conflicted/index states;
3. lane overlap reports distinguish temporary/rebased lanes from legitimate
   leased lanes and recommend moving the legitimate lane to the verified head
   instead of landing the temporary lane;
4. coverage hard-floor policy records the evidence-bound hard gate and keeps
   aspiration explicit instead of implicit;
5. reference-transaction regression covers both raw accepted-ref bypass blocking
   and official closeout admission.

The closeout evidence is recorded in
`evidence/chronicle/plan-residue-closeout-20260709/2026-07-09.md` and bounded by
`evidence/claims/plan-residue-closeout-20260709.toml`.

## Historical constraints

The original lane followed these constraints:

- Do not touch overlapping parity-owned files unless required.
- Keep names plain; no new obscure philosophical subsystem names.
- Prefer small diagnostics and tests over broad architecture churn.
- Preserve existing gates; do not add bypasses.

## Historical work items

1. Add dirty provenance to `workspace_status` and tests.
2. Add closeout/land failure guidance for `accepted_update_failed`,
   `work_lane_dirty`, `candidate_base_stale`, and scope overlap.
3. Add lane overlap migration recommendation in coordination/status payloads.
4. Add coverage policy record and architecture test binding the hard and
   aspirational floors.
5. Add focused ref-transaction official closeout regression.
6. Validate with focused tests, `ethos status`, `ethos status`, `ethos prove`,
   land/closeout/publish.
