"""Verify abandonment previews, current authority, and pre-effect refusals."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_retirement.abandonment as abandonment
import ethos.adapters.mutation.lane_retirement.operation as operation
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.lane_scenarios import apply_retirement_receipt
from tests.support.lane_scenarios import derive_abandonment
from tests.support.runtime_scenarios import install_fixture_hook_runtime


def test_reviewed_abandonment_projects_bounded_summary_without_dropping_manifest(
    divergent_lane,
):
    repo, lane = divergent_lane
    generated = lane / "build" / "runtime" / "tool-cache" / "probe"
    generated.mkdir(parents=True)
    for number in range(120):
        (generated / f"item-{number:03d}").write_text("regenerable\n", encoding="utf-8")

    report = derive_abandonment(repo, review_content=True)

    assert report["verdict"] == "pass"
    assert "request" not in report
    assert report["review_summary"]["entry_count"] >= 120
    assert report["review_summary"]["full_manifest"] == report["receipt"]["path"]
    assert len(json.dumps(report)) < 8_192
    receipt = report["receipt"]
    request = operation.load_operation(repo, receipt["path"], receipt["sha256"])
    assert all(
        f"build/runtime/tool-cache/probe/item-{number:03d}" in request.reviewed_content["entries"]
        for number in range(120)
    )


@pytest.mark.parametrize(
    ("lease_state", "reacquired"),
    [
        ("missing", False),
        ("expired", False),
        ("valid", False),
        ("missing", True),
        ("expired", True),
    ],
)
@pytest.mark.parametrize("historical", [False, True])
def test_reviewed_retirement_uses_current_coordination_not_historical_ownership(
    divergent_lane, monkeypatch, lease_state, reacquired, historical
):
    repo, lane = divergent_lane
    initial = derive_abandonment(repo)["receipt"]
    original = operation.load_operation(repo, initial["path"], initial["sha256"])
    operation.revoke_operation_lease(repo, original)
    if lease_state != "missing":
        acquire_lease(
            state_database(repo),
            lease=exact_lease(
                branch="work/abandon",
                holder_ref="agent:test:case:former",
                ttl_seconds=-1 if lease_state == "expired" else 86_400,
            ),
        )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:cleanup")
    if historical:
        git(lane, "reset", "--hard", git(repo, "rev-list", "--max-parents=0", "HEAD"))
    else:
        git(repo, "reset", "--hard", git(lane, "rev-parse", "HEAD"))
    assert install_fixture_hook_runtime(repo)["current"]
    target = lane / "reviewed.txt"
    target.write_text("adjudicated residual\n")
    admin = Path(git(lane, "rev-parse", "--absolute-git-dir"))
    before = (git(repo, "show-ref"), (admin / "index").read_bytes(), target.read_bytes())
    result = run_ethos_raw(
        "lane",
        "retire",
        "abandon",
        "--branch",
        "work/abandon",
        "--reason-code",
        "absorbed-content",
        "--reason",
        "current owner covers these bytes",
        "--review-content",
        "--json",
        cwd=repo,
    )
    report = json.loads(result.stdout)
    if lease_state == "valid":
        assert report["required_gaps"] == ["foreign_work_lane_retire_authority_required"]
    else:
        assert report["verdict"] == "pass", report["required_gaps"]
        assert "request" not in report["data"]
        assert report["data"]["review_summary"]["entry_count"] > 0
        receipt = report["data"]["receipt"]
        assert report["data"]["review_summary"]["full_manifest"] == receipt["path"]
        request = operation.load_operation(repo, receipt["path"], receipt["sha256"])
        assert request.lease_state == lease_state
        if reacquired:
            if lease_state == "expired":
                operation.revoke_operation_lease(repo, request)
            acquire_lease(
                state_database(repo),
                lease=exact_lease(branch="work/abandon", holder_ref="agent:test:case:new-owner"),
            )
        result = run_ethos_raw(
            "lane",
            "retire",
            "abandon",
            "--receipt",
            receipt["path"],
            "--receipt-sha256",
            receipt["sha256"],
            "--authorize",
            "--apply",
            "--json",
            cwd=repo,
        )
        report = json.loads(result.stdout)
        if not reacquired:
            assert report["state"] == "retired", report["required_gaps"]
            assert not lane.exists()
            assert not admin.exists()
            assert git(repo, "branch", "--list", "work/abandon") == ""
            assert observe_lease(state_database(repo), "work/abandon").state == "missing"
            return
        assert report["required_gaps"] == ["retirement_operation_state_drift"]
        assert observe_lease(state_database(repo), "work/abandon").state == "valid"
    assert report["verdict"] == "block"
    assert before == (git(repo, "show-ref"), (admin / "index").read_bytes(), target.read_bytes())


@pytest.mark.parametrize("fault", ["symlink", "locked", "reattached", "head"])
def test_retirement_observes_replaced_or_locked_root_as_drift(divergent_lane, fault):
    repo, lane = divergent_lane
    detached = fault in {"reattached", "head"}
    if detached:
        git(lane, "switch", "--detach")
    derived = derive_abandonment(repo, review_content=detached, path=lane if detached else None)
    receipt = derived["receipt"]
    request = operation.load_operation(repo, receipt["path"], receipt["sha256"])
    retained = lane
    if fault == "symlink":
        retained = lane.with_name("relocated")
        lane.rename(retained)
        lane.symlink_to(retained, target_is_directory=True)
    elif fault == "locked":
        git(repo, "worktree", "lock", lane.as_posix())
    else:
        git(lane, "switch", "work/abandon") if fault == "reattached" else git(
            lane, "reset", "--soft", "HEAD^"
        )
    before = git(repo, "show-ref")

    assert operation.observe_operation(repo, request).worktree_state == "moved"
    report = apply_retirement_receipt(repo, receipt)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["retirement_operation_state_drift"]
    assert git(repo, "show-ref") == before
    assert (retained / "abandoned.txt").read_text() == "abandoned\n"
    assert observe_lease(state_database(repo), "work/abandon").state == "valid"


@pytest.mark.parametrize(
    ("fault", "gap"),
    [
        ("branch", "lane_abandonment_branch_invalid"),
        ("missing", "lane_abandonment_coordinates_unavailable"),
        ("control", "retirement_control_root_unavailable"),
        ("absorbed", "lane_abandonment_divergence_required"),
        ("descendant", "lane_abandonment_divergence_required"),
        ("ambiguous", "lane_abandonment_worktree_ambiguous"),
        ("dirty", "retirement_content_review_required"),
        ("lease", "work_lane_lease_missing"),
        ("actor", "invocation_actor_missing"),
        ("foreign", "foreign_work_lane_retire_authority_required"),
        ("code", "lane_abandonment_reason_invalid"),
        ("reason", "lane_abandonment_reason_invalid"),
        ("mode", "lane_retirement_receipt_mode_invalid"),
    ],
)
def test_abandonment_rejects_invalid_current_facts_without_effects(
    divergent_lane, monkeypatch, fault, gap
):
    repo, lane = divergent_lane
    valid = derive_abandonment(repo)
    assert valid["state"] == "derived", valid
    receipt = valid["receipt"]
    request = operation.load_operation(repo, receipt["path"], receipt["sha256"])
    arguments = {}
    if fault in {"branch", "missing"}:
        arguments["branch"] = "dev" if fault == "branch" else "work/missing"
    elif fault == "control":
        git(repo, "switch", "-c", "other")
    elif fault in {"absorbed", "descendant"}:
        target = (
            request.head if fault == "absorbed" else git(repo, "merge-base", "dev", request.head)
        )
        git(repo, "reset", "--hard", target)
    elif fault == "ambiguous":
        status = abandonment.workspace_status(repo)
        worktrees = status["worktrees"]
        assert isinstance(worktrees, list)
        row = next(row for row in worktrees if row["branch"] == "work/abandon")
        worktrees.append(dict(row))
        monkeypatch.setattr(abandonment, "workspace_status", lambda _root: status)
    elif fault == "dirty":
        (lane / "abandoned.txt").write_text("preserve uncommitted work\n", encoding="utf-8")
    elif fault == "lease":
        operation.revoke_operation_lease(repo, request)
    elif fault in {"actor", "foreign"}:
        monkeypatch.setenv("ETHOS_ACTOR", "" if fault == "actor" else "agent:test:case:foreign")
    elif fault in {"code", "reason"}:
        arguments["reason_code" if fault == "code" else "reason"] = (
            "INVALID" if fault == "code" else " "
        )
    else:
        receipt = operation.persist_operation(repo, request.model_copy(update={"mode": "landed"}))

    def state():
        return (
            git(repo, "show-ref"),
            git(repo, "worktree", "list", "--porcelain"),
            (lane / "abandoned.txt").read_bytes(),
            observe_lease(state_database(repo), "work/abandon"),
            tuple(sorted(operation.operation_store(repo).iterdir())),
        )

    before = state()
    receipt_path, receipt_sha256 = receipt["path"], receipt["sha256"]
    assert isinstance(receipt_path, str)
    assert isinstance(receipt_sha256, str)
    report = (
        operation.execute_retirement_operation(
            expected_mode="abandon",
            root=repo,
            receipt_path=receipt_path,
            receipt_sha256=receipt_sha256,
            apply=True,
            authorized=True,
        )
        if fault == "mode"
        else derive_abandonment(
            repo,
            branch=arguments.get("branch", "work/abandon"),
            reason_code=arguments.get("reason_code", "superseded-experiment"),
            reason=arguments.get("reason", "discard divergent experiment"),
        )
    )
    assert report["state"] == "blocked"
    assert report["required_gaps"] == [gap]
    assert state() == before


def test_abandonment_apply_requires_authorization_before_loading_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        operation,
        "load_operation",
        lambda *_args: pytest.fail("unauthorized abandonment must not load or execute"),
    )

    report = operation.execute_retirement_operation(
        root=tmp_path,
        receipt_path="/receipt",
        receipt_sha256="sha256:" + "d" * 64,
        apply=True,
        authorized=False,
    )

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["authorization_required"]
