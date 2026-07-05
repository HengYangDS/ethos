---
subject: ethos:evidence:unbound-work-lane-ref-visibility
role: evidence
state: active
relations:
  supports: ethos-unbound-work-lane-ref-visibility
---

# Unbound Work Lane Ref Visibility Evidence - 2026-07-06

This evidence records the status and coordination hardening that exposes
configured Work Lane branch refs even when no linked Git worktree exists.

## Scope

- Added an OpenSpec carrier at
  `openspec/changes/archive/2026-07-05-expose-unbound-work-lane-refs`.
- Extended `ethos status --json` so `branch_bindings` includes unbound
  configured `work/*` refs with `role=work_lane` and
  `worktree_binding=unbound`.
- Kept `foreign_work_lanes` scoped to linked worktrees whose dirty paths,
  path scope, and leases can be inspected.
- Added `coordination.unbound_work_lane_count` and advisory gap
  `unbound_work_lane_ref_present`.
- Updated workspace status schema, schema fixtures, unit tests, CLI contract
  tests, and terminal governance docs.

## Boundary

Unbound Work Lane refs are Git repository facts. They are not mutation-capable
active lanes, not foreign worktrees, and not blocking closeout gaps by
themselves. Branch details stay in `branch_bindings`; coordination only reports
count and advisory signal.

## Verification

Commands run from `work/expose-unbound-work-lane-refs`:

```bash
openspec status --change expose-unbound-work-lane-refs --json
uv run --group dev pytest tests/unit/lanes/test_lanes.py::test_workspace_status_reports_foreign_work_lanes_without_reading_them tests/unit/lanes/test_lanes.py::test_workspace_status_reports_unbound_work_lane_ref_without_active_lane tests/unit/lanes/test_lanes.py::test_workspace_status_reports_branch_worktree_bindings_without_ui_actions tests/unit/cli/test_contracts.py::test_status_reports_unbound_work_lane_ref_as_advisory_signal tests/unit/governance/test_validation_gates.py::test_workspace_status_payload_validates_worktree_bindings -q
uv run --group dev ruff check packages/ethos/src/ethos/adapters/repo/status.py packages/ethos/src/ethos/adapters/repo/coordination.py tests/unit/lanes/test_lanes.py tests/unit/cli/test_contracts.py tests/unit/governance/test_validation_gates.py
```

Observed results:

- OpenSpec carrier: complete planning artifacts for
  `expose-unbound-work-lane-refs`.
- Focused status/schema/CLI tests: `5 passed`.
- Ruff check: all checks passed.
- Live status on this lane exposed the existing unbound
  `work/dissolve-cache-table` ref in `branch_bindings`, while
  `foreign_work_lanes=[]` and `coordination.blocking=false`.

The carrier was archived through official OpenSpec archive semantics as
`openspec/changes/archive/2026-07-05-expose-unbound-work-lane-refs` with
archive metadata `.openspec.yaml`. Further
full proof is run after this claim digest is refreshed and the repository HEAD
is finalized.
