from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from ethos.adapters.mutation.lane_resolution import apply_lane_resolution
from ethos.adapters.mutation.lane_resolution import plan_lane_resolution
from ethos.repository.policy.schema import validate_schema_instance
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path


def _orphan_lane(tmp_path: Path) -> tuple[Path, Path]:
    repo = init_repo(tmp_path / "repo")
    lane = tmp_path / "repo-work-orphan"
    git(repo, "worktree", "add", "-b", "work/orphan", lane.as_posix(), "dev")
    return repo, lane


def test_exceptional_resolution_recomputes_observation_before_effect(tmp_path: Path) -> None:
    repo, lane = _orphan_lane(tmp_path)
    decision_path = tmp_path / "decision.json"
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Unknown owner; block mutation.",
        evidence_refs=("evidence:review",),
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )
    assert planned["ok"] is True
    (lane / "README.md").write_text("# changed after decision\n", encoding="utf-8")

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert applied["ok"] is False
    assert "lane_resolution_observation_stale" in applied["required_gaps"]


def test_preserve_resolution_writes_recovery_package_and_completion_receipt(tmp_path: Path) -> None:
    repo, lane = _orphan_lane(tmp_path)
    (lane / "README.md").write_text("# dirty preserved\n", encoding="utf-8")
    decision_path = tmp_path / "decision.json"
    plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve",
        reason="Preserve owner-unknown work.",
        evidence_refs=("evidence:review",),
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert applied["ok"] is True
    package = applied["preservation_package"]
    assert (repo / package["path"] / "manifest.json").is_file()
    assert applied["receipt"]["completed"] is True
    assert applied["receipt"]["disposition"] == "preserve"
    assert git(repo, "show-ref", "--verify", "refs/heads/work/orphan")


def test_preserve_resolution_includes_non_ignored_untracked_files(tmp_path: Path) -> None:
    repo, lane = _orphan_lane(tmp_path)
    (lane / "notes.txt").write_text("owner-unknown work\n", encoding="utf-8")
    decision_path = tmp_path / "decision.json"
    plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve",
        reason="Preserve all recoverable work.",
        evidence_refs=("evidence:review",),
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    package = repo / applied["preservation_package"]["path"]
    assert (package / "untracked.tar").is_file()
    assert (
        "notes.txt"
        in subprocess.run(
            ["tar", "-tf", (package / "untracked.tar").as_posix()],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )


def test_resolution_decision_and_receipt_validate_against_kernel_schemas(
    tmp_path: Path,
) -> None:
    repo, _ = _orphan_lane(tmp_path)
    decision_path = tmp_path / "decision.json"
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Keep ambiguous state intact.",
        evidence_refs=("evidence:review",),
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )
    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert (
        validate_schema_instance(
            "lane-resolution-decision.schema.json", planned["decision"], root=repo
        )["ok"]
        is True
    )
    assert (
        validate_schema_instance(
            "lane-resolution-receipt.schema.json", applied["receipt"], root=repo
        )["ok"]
        is True
    )


def test_resolution_rejects_tampered_schema_constants(tmp_path: Path) -> None:
    repo, _ = _orphan_lane(tmp_path)
    decision_path = tmp_path / "decision.json"
    plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Keep ambiguous state intact.",
        evidence_refs=("evidence:review",),
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision["mints_authority"] = True
    decision_path.write_text(json.dumps(decision), encoding="utf-8")

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert applied["ok"] is False
    assert "lane_resolution_decision_invalid" in applied["required_gaps"]


def test_resolution_decide_does_not_write_tracked_chronicle_path(tmp_path: Path) -> None:
    repo, _ = _orphan_lane(tmp_path)
    decision_path = repo / "evidence" / "chronicle" / "decision.json"

    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Keep ambiguous state intact.",
        evidence_refs=("evidence:review",),
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )

    assert planned["ok"] is False
    assert "lane_resolution_decision_path_not_local_artifact" in planned["required_gaps"]
    assert not decision_path.exists()


def test_retire_resolution_requires_clean_target_and_irreversible_confirmation(
    tmp_path: Path,
) -> None:
    repo, lane = _orphan_lane(tmp_path)
    decision_path = tmp_path / "decision.json"
    plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="retire",
        reason="Reviewed obsolete lane.",
        evidence_refs=("evidence:maintainer-decision",),
        decision_path=decision_path,
        break_glass=True,
        apply=True,
    )

    blocked = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )
    assert "irreversible_confirmation_required" in blocked["required_gaps"]

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )
    assert applied["ok"] is True
    assert not lane.exists()
    assert (
        subprocess.run(
            ["git", "show-ref", "--verify", "refs/heads/work/orphan"],
            cwd=repo,
            check=False,
        ).returncode
        != 0
    )


def test_break_glass_requires_reconciliation_receipt(tmp_path: Path) -> None:
    repo, _ = _orphan_lane(tmp_path)
    decision_path = tmp_path / "decision.json"
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Emergency containment.",
        evidence_refs=("evidence:incident",),
        decision_path=decision_path,
        break_glass=True,
        apply=True,
    )
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    assert decision["break_glass"] is True

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )
    assert planned["ok"] is True
    assert applied["receipt"]["reconciliation_required"] is True
