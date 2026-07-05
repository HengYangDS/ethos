---
subject: ethos:coordination-next-action
role: evidence
state: complete
---

# Coordination Next Action Evidence — 2026-07-06

## Claim

ETHOS status now distinguishes blocking Work Lane coordination remediation from
advisory coordination cleanup in `data.coordination.next_action`.

## Evidence

- Focused tests passed:
  - `tests/unit/lanes/test_lanes.py::test_workspace_status_reports_foreign_work_lanes_without_reading_them`
  - `tests/unit/lanes/test_lanes.py::test_workspace_status_reports_unbound_work_lane_ref_without_active_lane`
  - `tests/unit/cli/test_contracts.py::test_status_reports_unbound_work_lane_ref_as_advisory_signal`
  - `tests/unit/coverage/test_core_state_claims_edges.py::test_git_and_coordination_edges`
- Formatting and lint passed for touched Python files.
- Live `ethos status --json` in the Work Lane reports advisory-only unbound Work
  Lane refs with `next_action = inspect or retire unbound Work Lane refs during
  coordination cleanup`.

## Boundary

This evidence supports a read-model precision change only. It does not claim
remote publication, hosted CI success, or a new Work Lane ontology.

## Closeout

OpenSpec archive path: `openspec/changes/archive/2026-07-05-refine-coordination-next-action`.
- Archive metadata: `openspec/changes/archive/2026-07-05-refine-coordination-next-action/.openspec.yaml`.
