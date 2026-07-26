"""Reusable current-record facts for lane-resolution tests."""

from pathlib import Path

from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from tests.support.contract_helpers import write_chronicle_decision


def entry_identity(path: Path) -> tuple[int, int, int]:
    """Return one no-follow filesystem identity used by clear tests."""
    metadata = path.stat(follow_symlinks=False)
    return metadata.st_dev, metadata.st_ino, metadata.st_mode


def preserve_lane(repo: Path, lane: Path) -> dict[str, object]:
    """Preserve one exact test lane and return its applied result."""
    (lane / "README.md").write_text("# preserve\n", encoding="utf-8")
    decision_path = current_record_root(repo) / "decisions/test-preserve.json"
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve",
        reason="Preserve this exact lane state.",
        evidence_refs=("evidence:current-enumeration",),
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-current-enumeration", token="preserve"
        ),
        recovery_plan="Retain the exact observed bytes.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )
    assert planned["ok"] is True
    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )
    assert applied["ok"] is True
    return applied
