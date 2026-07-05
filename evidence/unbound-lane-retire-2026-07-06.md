# Evidence: unbound-lane-retire

Scope: add a governed local cleanup path for unbound Work Lane refs.

Commands:

```text
uv run --group dev ruff check packages/ethos/src/ethos/adapters/mutation/lanes.py packages/ethos/src/ethos/surface/cli/lane.py tests/unit/lanes/test_lanes.py tests/unit/cli/test_contracts.py
# All checks passed.

uv run --group dev pytest tests/unit/lanes/test_lanes.py::test_retire_unbound_work_lane_ref_dry_run_reports_head_bound_plan tests/unit/lanes/test_lanes.py::test_retire_unbound_work_lane_ref_apply_deletes_only_matching_ref tests/unit/lanes/test_lanes.py::test_retire_unbound_work_lane_ref_blocks_head_mismatch tests/unit/lanes/test_lanes.py::test_retire_unbound_work_lane_ref_blocks_linked_worktree tests/unit/lanes/test_lanes.py::test_retire_unbound_work_lane_ref_requires_reason_authorization_and_head tests/unit/cli/test_contracts.py::test_lane_retire_unbound_apply_removes_matching_ref tests/unit/cli/test_contracts.py::test_lane_retire_unbound_apply_requires_authorization -q
# 7 passed
```

Design binding:

- Uses the existing status read model as the admission source.
- Uses a head-bound Git ref transaction for deletion.
- Separates local unbound residue cleanup from linked Work Lane retirement and
  remote deletion.

Live repository smoke after implementation:

```text
ETHOS_ROOT=$PWD uv run --group dev ethos lane retire-unbound --branch work/dissolve-cache-table --expect-head 4e8b5413fb26778211353732162a59bd66d600b8 --reason "superseded by accepted-root cache table dissolution and later parity evidence" --json
# ok=true, state=ready_to_retire_unbound

ETHOS_ROOT=$PWD uv run --group dev ethos lane retire-unbound --branch work/dissolve-cache-table --expect-head 4e8b5413fb26778211353732162a59bd66d600b8 --reason "superseded by accepted-root cache table dissolution and later parity evidence" --authorize --apply --json
# ok=true, state=retired_unbound, retired_ref=refs/heads/work/dissolve-cache-table
```
