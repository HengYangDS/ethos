from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.contracts.resolution.lane import LaneResolutionPlanRequest
from tests.support.contract_helpers import git
from tests.support.lane_helpers import orphan_work_lane

if TYPE_CHECKING:
    from pathlib import Path


def _commit_bytes(repo: Path, relative: str, raw: bytes) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    git(repo, "add", relative)
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        f"add {relative}",
    )


def test_accepted_chronicle_matches_working_and_tree_bytes_exactly(tmp_path: Path) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    relative = "evidence/chronicle/example.md"
    raw = b"decision: lane_resolution/retire\r\n"
    _commit_bytes(repo, relative, raw)

    planned = plan_lane_resolution(
        root=repo,
        request=LaneResolutionPlanRequest(
            branch="work/orphan",
            chronicle_ref=relative,
            disposition="retire",
            reason="Retire the exact observed lane.",
            evidence_refs=("evidence:maintainer-decision",),
            recovery_plan="The committed chronicle preserves the decision.",
            decision_path=(current_record_root(repo) / "decisions" / "retire.json").as_posix(),
            break_glass=True,
            apply=True,
        ),
    )

    decision = planned["decision"]
    assert isinstance(decision, dict)
    assert planned["ok"] is True
    assert decision["chronicle_ref"] == relative
    assert decision["chronicle_digest"] == hashlib.sha256(raw).hexdigest()
