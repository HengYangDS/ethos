"""Continue retirement from current facts after an accepted advance invalidates its receipt."""

from __future__ import annotations

import json
import shlex
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_retirement.operation as operation
from ethos.adapters.mutation.lane_retirement.abandonment import derive_lane_abandonment
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.retirement import RetirementObservation
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.lane_scenarios import apply_retirement_receipt
from tests.support.lane_scenarios import derive_abandonment
from tests.support.lane_scenarios import retirement_request


def _command(command: object) -> tuple[list[str], dict[str, str]]:
    words = shlex.split(str(command))
    values = {
        word: words[index + 1]
        for index, word in enumerate(words[:-1])
        if word.startswith("--") and not words[index + 1].startswith("--")
    }
    return words, values


def _derive_advertised(repo: Path, command: object) -> dict[str, object]:
    """Run the advertised abandonment derivation through its public owner."""
    words, values = _command(command)
    assert words[:4] == ["ethos", "lane", "retire", "abandon"], command
    assert values["--root"] == repo.as_posix()
    return derive_lane_abandonment(
        root=repo,
        branch=values.get("--branch", ""),
        path=values.get("--path", ""),
        reason_code=values["--reason-code"],
        reason=values["--reason"],
        review_content="--review-content" in words,
    )


def _advance_accepted(repo: Path, name: str) -> str:
    return commit_fixture_file(repo, f"{name}.txt", f"{name}\n", f"advance accepted: {name}")


@pytest.mark.parametrize("accepted", ["advanced", "moved", "absent", "unavailable"])
def test_only_a_fast_forward_keeps_receipt_progress_observable(tmp_path, accepted):
    observation = RetirementObservation(
        worktree_state="absent",
        ref_state="expected",
        lease_state="expected",
        accepted_state=accepted,
    )
    request = retirement_request(tmp_path)
    if accepted != "advanced":
        with pytest.raises(ValueError, match="retirement_operation_state_drift"):
            operation.reduce_progress(request, observation)
        return
    progress = operation.reduce_progress(request, observation)
    assert (progress.state, progress.completed_effects) == (
        "partial_transition",
        ("remove_worktree",),
    )


def test_accepted_advance_before_apply_requires_a_fresh_review(divergent_lane):
    repo, lane = divergent_lane
    receipt = derive_abandonment(repo, review_content=True)["receipt"]
    _advance_accepted(repo, "after-review")

    result = apply_retirement_receipt(repo, receipt)

    assert result["required_gaps"] == ["retirement_accepted_coordinate_drift"], result
    assert (result["state"], result["completed_effects"]) == ("blocked", [])
    assert lane.is_dir()
    fresh = _derive_advertised(repo, result["next_action"])
    assert fresh["verdict"] == "pass", fresh
    assert apply_retirement_receipt(repo, fresh["receipt"])["state"] == "retired"
    assert not lane.exists()
    assert git(repo, "branch", "--list", "work/abandon") == ""


@pytest.mark.parametrize("relation", ["divergent", "absorbed"])
def test_accepted_advance_after_removal_keeps_progress_and_continues(
    divergent_lane, monkeypatch, relation
):
    repo, lane = divergent_lane
    receipt = derive_abandonment(repo, review_content=True)["receipt"]
    head = operation.load_operation(repo, receipt["path"], receipt["sha256"]).head
    native_removal = operation.remove_operation_worktree

    def remove_then_advance(root: Path, request: operation.RetirementOperation) -> None:
        native_removal(root, request)
        if relation == "absorbed":
            git(repo, "merge", "--no-ff", "--no-edit", "work/abandon")
        else:
            _advance_accepted(repo, "after-removal")

    monkeypatch.setattr(operation, "remove_operation_worktree", remove_then_advance)
    result = apply_retirement_receipt(repo, receipt)

    assert result["required_gaps"] == ["retirement_accepted_coordinate_drift"], result
    assert result["state"] == "partial_transition"
    assert result["completed_effects"] == ["remove_worktree"]
    assert result["remaining_effects"] == ["delete_ref", "revoke_lease"]
    persisted = json.loads(Path(str(result["progress_receipt"]["path"])).read_text())
    assert (persisted["state"], persisted["completed_effects"]) == (
        "partial_transition",
        ["remove_worktree"],
    )
    assert not lane.exists()
    assert git(repo, "rev-parse", "refs/heads/work/abandon") == head
    words, values = _command(result["next_action"])
    if relation == "absorbed":
        assert words[:4] == ["ethos", "lane", "retire", "superseded"]
        assert [values[key] for key in ("--branch", "--path", "--expect-head")] == [
            "work/abandon",
            lane.as_posix(),
            head,
        ]
        assert values["--absorbed-by"] == git(repo, "rev-parse", "dev")
        return
    fresh = _derive_advertised(repo, result["next_action"])
    assert fresh["verdict"] == "pass", fresh
    assert apply_retirement_receipt(repo, fresh["receipt"])["state"] == "retired"
    assert git(repo, "branch", "--list", "work/abandon") == ""
    assert observe_lease(state_database(repo), "work/abandon").state == "missing"


def test_dry_run_after_accepted_advance_writes_no_progress(divergent_lane):
    repo, lane = divergent_lane
    receipt = derive_abandonment(repo, review_content=True)["receipt"]
    _advance_accepted(repo, "before-dry-run")
    store = operation.local_state_root(repo) / "operations" / "lane-retirement"
    before = sorted(store.rglob("*")) if store.exists() else []

    report = operation.execute_retirement_operation(
        root=repo,
        receipt_path=receipt["path"],
        receipt_sha256=receipt["sha256"],
        apply=False,
        authorized=False,
    )

    assert report["required_gaps"] == ["retirement_accepted_coordinate_drift"], report
    assert _command(report["next_action"])[0][:4] == ["ethos", "lane", "retire", "abandon"]
    assert (sorted(store.rglob("*")) if store.exists() else []) == before
    assert lane.is_dir()
