"""Coverage closure for mutation lane helpers."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ethos.adapters.mutation import lanes
from ethos.adapters.mutation.lane_lifecycle import lease
from ethos.adapters.mutation.lane_lifecycle import refresh
from ethos.adapters.mutation.lane_lifecycle.projection_rebase import core as projection
from ethos.adapters.mutation.lane_retirement.landed import core as landed
from ethos.adapters.mutation.lane_retirement.shared import core as shared
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT as ACCEPTED
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE as WORK


def _patch(monkeypatch: pytest.MonkeyPatch, target: object, **values: object) -> None:
    for name, value in values.items():
        monkeypatch.setattr(target, name, value)


def test_lane_reader_helpers(tmp_path: Path) -> None:
    find = lanes._status_work_lane  # noqa: SLF001, RUF100 - reader edges
    root = lanes._state_root  # noqa: SLF001, RUF100 - root fallback edges
    row = {"branch": "work/x", "role": WORK, "path": "/x"}
    actual = [find({"worktrees": "bad"}, "work/x"), find({"worktrees": ["bad", row]}, "work/x"), find({"worktrees": [{"branch": "work/y", "role": WORK}]}, "work/x")]  # fmt: skip
    assert actual == [None, row, None]
    accepted = {"worktrees": ["bad", {"role": ACCEPTED, "path": "/accepted"}]}
    assert [root(accepted, tmp_path), root({"worktrees": "bad"}, tmp_path), root({"worktrees": [{"role": WORK}]}, tmp_path)] == [Path("/accepted"), tmp_path, tmp_path]  # fmt: skip


def test_lane_start_and_lease_edges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policy = SimpleNamespace(candidate_branch="candidate/dev", work_branch=lambda name: f"work/{name}")  # fmt: skip
    _patch(monkeypatch, lanes, repo_root=lambda root: root, load_branch_role_policy=lambda _root: policy)  # fmt: skip

    def start(**values: object) -> dict[str, object]:
        holder = str(values.pop("holder_ref", "agent:test:case:owner"))
        return lanes.start_work_lane(root=tmp_path, name="x", holder_ref=holder, **values)

    assert [start(holder_ref="bad")["required_gaps"], start()["state"]] == [["holder_ref_invalid"], "planned"]  # fmt: skip
    candidate = {"exists": True, "worktree_exists": True, "worktree_path": str(tmp_path), "head": "h"}  # fmt: skip
    status = {"role": ACCEPTED, "dirty": False, "candidate": candidate}
    _patch(monkeypatch, lanes, workspace_status=lambda _root: status, changed_paths=lambda _root: [], _branch_exists=lambda *_args: True)  # fmt: skip
    assert start(apply=True)["required_gaps"] == ["branch_already_exists"]
    _patch(monkeypatch, lanes, _branch_exists=lambda *_args: False, run_git=lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stderr="boom"))  # fmt: skip
    failed = start(apply=True)
    assert (failed["required_gaps"], failed["stderr"]) == (["worktree_add_failed"], "boom")
    values = {"branch": "work/x", "expect_head": "h", "holder_ref": "bad", "lease_id": "l"}
    expected, gaps = lease._lease_expected_state(tmp_path, values)  # noqa: SLF001, RUF100 - holder edge  # fmt: skip
    assert (gaps, expected["holder_ref"]) == (("holder_ref_invalid",), "bad")
    with pytest.raises(ValueError, match="lease_operation_unknown:nope"):
        lease._apply_lease_effect("nope", tmp_path / "db", {}, {})  # noqa: SLF001, RUF100 - operation edge  # fmt: skip


def test_refresh_projection_and_retirement_edges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # fmt: skip
    candidate = {"exists": True, "worktree_exists": False, "worktree_path": str(tmp_path / "candidate"), "head": "c"}  # fmt: skip
    status = {"role": ACCEPTED, "dirty": False, "candidate": candidate}
    _patch(monkeypatch, refresh, repo_root=lambda root: root, load_branch_role_policy=lambda _root: SimpleNamespace(candidate_branch="candidate/dev"), workspace_status=lambda _root: status, changed_paths=lambda _root: [])  # fmt: skip

    def git(_root: Path, *args: str, **_kwargs: object) -> SimpleNamespace:
        failed = args[:2] in (("worktree", "add"), ("reset", "--hard"))
        return SimpleNamespace(returncode=int(failed), stdout="h\n" if args == ("rev-parse", "HEAD") else "", stderr="boom")  # fmt: skip

    monkeypatch.setattr(refresh, "run_git", git)
    first = refresh.bootstrap_candidate(root=tmp_path, path=tmp_path / "new", apply=True)
    candidate["worktree_exists"] = True
    second = refresh.refresh_candidate_from_accepted(root=tmp_path, apply=True, authorized=True, expect_head="h")  # fmt: skip
    assert [first["required_gaps"], second["required_gaps"]] == [["candidate_worktree_add_failed"], ["candidate_refresh_from_accepted_failed"]]  # fmt: skip
    claim = tmp_path / "evidence/claims" / f"{projection.SOURCE_BUDGET_SCOPE_CLAIM_ID}.toml"
    claim.parent.mkdir(parents=True)
    claim.write_text("[broken", encoding="utf-8")
    assert projection.archived_source_budget_scope_bound(tmp_path, list(projection.SOURCE_BUDGET_SCOPE_PATHS)) is False  # fmt: skip
    assert landed._retirement_control_root([{"role": WORK, "path": str(tmp_path)}]) is None  # noqa: SLF001, RUF100 - control root edge  # fmt: skip
    path = tmp_path / ".cache/local-state/worktree/leases.json"
    path.parent.mkdir(parents=True)
    for payload in ([], {"leases": "bad"}, {"leases": [{"branch": "work/y"}]}):
        path.write_text(json.dumps(payload), encoding="utf-8")
        before = path.read_bytes()
        assert (shared.delete_json_projection_lease(tmp_path, subject="work/x"), path.read_bytes()) == (0, before)  # fmt: skip
