from __future__ import annotations

import inspect
import subprocess

import ethos.adapters.mutation.lane_retirement.core as superseded
import ethos.adapters.mutation.lane_retirement.landed.core as landed
import ethos.adapters.mutation.lane_retirement.shared.core as shared
import ethos.adapters.mutation.lane_retirement.unbound.core as unbound


def test_retirement_runtime_compatibility_surface() -> None:
    def run_git(_root: object, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, "", "")

    runtime = shared.RetirementRuntime(run_git=run_git)
    assert (
        superseded.SupersededRetirementRuntime(run_git=run_git, shared=runtime).run_git is run_git
    )
    assert landed.LandedRetirementRuntime(shared=runtime).shared is runtime
    assert unbound.UnboundRetirementRuntime(shared=runtime).shared is runtime
    for target in (
        superseded.retire_superseded_work_lane,
        landed.retire_landed_work_lanes,
        unbound.retire_unbound_work_lane_ref,
        shared.remove_linked_lane,
    ):
        assert "runtime" in inspect.signature(target).parameters
