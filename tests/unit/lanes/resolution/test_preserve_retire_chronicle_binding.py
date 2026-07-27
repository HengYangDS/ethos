from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.mutation.resolution.closeout.recovery as recovery_adapter
from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.mutation.resolution.observation import observe_lane
from ethos.adapters.mutation.resolution.records.roots import accepted_control_root
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.contracts.resolution.lane import LaneResolutionPlanRequest
from tests.support.contract_helpers import commit_fixture_file
from tests.support.lane_helpers import orphan_work_lane

if TYPE_CHECKING:
    import pytest


def _bound_chronicle(root: Path, *, revision: str) -> str:
    branch = "work/orphan"
    control_root = accepted_control_root(root)
    observation, gaps = observe_lane(control_root, branch)
    assert gaps == []
    relative = "evidence/chronicle/target-binding/preserve-retire.md"
    commit_fixture_file(
        control_root,
        relative,
        "---\n"
        "event: lane_resolution/preserve-retire\n"
        f"target_branch: {observation.lane_ref}\n"
        f"target_head: {observation.head}\n"
        f"---\n\nrevision: {revision}\n",
        f"record target-bound chronicle {revision}",
    )
    return relative


def test_preserve_retire_rechecks_chronicle_after_preservation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    (lane / "README.md").write_text("# preserve then bind\n", encoding="utf-8")
    chronicle_ref = _bound_chronicle(repo, revision="one")
    planned = plan_lane_resolution(
        root=repo,
        request=LaneResolutionPlanRequest(
            branch="work/orphan",
            disposition="preserve-retire",
            reason="Preserve the exact diverged predecessor before retirement.",
            evidence_refs=("evidence:maintainer-decision",),
            chronicle_ref=chronicle_ref,
            recovery_plan="Preserve the observed target before any destructive effect.",
            decision_path=(
                current_record_root(repo) / "decisions" / "preserve-retire.json"
            ).as_posix(),
            break_glass=True,
            apply=True,
        ),
    )
    prepare = recovery_adapter.prepare_resolution_effect

    def replace_chronicle(
        **kwargs: object,
    ) -> tuple[dict[str, object], dict[str, object], str, str]:
        result = prepare(**kwargs)
        _bound_chronicle(repo, revision="two")
        return result

    monkeypatch.setattr(recovery_adapter, "prepare_resolution_effect", replace_chronicle)
    applied = apply_lane_resolution(
        root=repo,
        decision_path=Path(str(planned["decision_path"])),
        confirm_irreversible=True,
        apply=True,
    )

    assert planned["ok"] is True
    assert applied["required_gaps"] == ["lane_resolution_chronicle_stale"]
    assert lane.is_dir()


def test_preserve_retire_completes_from_one_bound_public_decision(tmp_path: Path) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    (lane / "README.md").write_text("# preserve then retire\n", encoding="utf-8")
    chronicle_ref = _bound_chronicle(repo, revision="complete")
    planned = plan_lane_resolution(
        root=repo,
        request=LaneResolutionPlanRequest(
            branch="work/orphan",
            disposition="preserve-retire",
            reason="Preserve the exact observed predecessor before retirement.",
            evidence_refs=("evidence:maintainer-decision",),
            chronicle_ref=chronicle_ref,
            recovery_plan="Preserve the observed target before the irreversible closeout.",
            decision_path=(
                current_record_root(repo) / "decisions" / "preserve-retire-complete.json"
            ).as_posix(),
            break_glass=True,
            apply=True,
        ),
    )
    applied = apply_lane_resolution(
        root=repo,
        decision_path=Path(str(planned["decision_path"])),
        confirm_irreversible=True,
        apply=True,
    )
    assert planned["ok"] is True
    assert applied["ok"] is True
    assert not lane.exists()
    receipt = applied["receipt"]
    assert isinstance(receipt, dict)
    assert receipt["state"] == "preserved_and_retired"
