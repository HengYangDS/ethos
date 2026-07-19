from __future__ import annotations

import json
from typing import TYPE_CHECKING

import ethos.adapters.mutation.lane_retirement.shared.core as retirement_shared
import ethos.adapters.mutation.lane_retirement.unbound.core as retirement
from ethos.adapters.repo.dirty.core import dirty_provenance
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path

_CLAIM_ID = "exceptional-unbound-test-claim"
_CHRONICLE_REF = "evidence/chronicle/exceptional-unbound-test/2026-07-19.md"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")


def _exceptional_fixture(tmp_path: Path) -> tuple[Path, str, str, str]:
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "main", "dev")
    branch = "work/stale-ref"
    git(repo, "branch", branch, "dev")
    head = git(repo, "rev-parse", branch)
    _write(
        repo / f"evidence/claims/{_CLAIM_ID}.toml",
        f'[claim]\nid = "{_CLAIM_ID}"\nsubject = "ethos:test:exceptional-unbound"\nstate = "active"\n',
    )
    _write(
        repo / _CHRONICLE_REF,
        f"event: lane_retire/unbound_exceptional\ntarget_branch: {branch}\ntarget_head: {head}\ntarget_claim: {_CLAIM_ID}\n",
    )
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "accept policy",
    )
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    return repo, branch, head, _CHRONICLE_REF


def _retire(repo: Path, branch: str, head: str, chronicle: str, **changes):
    request = {
        "root": repo,
        "branch": branch,
        "expect_head": head,
        "reason": "accepted truth contains the source",
        "chronicle_ref": chronicle,
    }
    return retirement.retire_unbound_work_lane_ref(**(request | changes))


def test_exceptional_retirement_contract_matrix(tmp_path: Path) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path / "plan")
    missing = _retire(repo, branch, head, "")
    assert missing["required_gaps"] == ["unbound_retire_chronicle_ref_required"]
    planned = _retire(repo, branch, head, chronicle)
    assert (planned["state"], planned["required_gaps"]) == (
        "ready_to_retire_unbound_exceptional",
        [],
    )
    blocked = _retire(repo, branch, head, chronicle, apply=True, authorized=True)
    assert blocked["required_gaps"] == [
        "irreversible_confirmation_required",
        "unbound_retire_requires_break_glass",
    ]
    live_repo, live_branch, live_head, live_chronicle = _exceptional_fixture(tmp_path / "live")
    retired = _retire(
        live_repo,
        live_branch,
        live_head,
        live_chronicle,
        apply=True,
        authorized=True,
        break_glass=True,
        confirm_irreversible=True,
    )
    assert retired["state"] == "retired_unbound_exceptional"
    assert all(retired["receipt"]["postconditions"].values())


def test_projection_and_dirty_support(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "dirty")
    (repo / "new.txt").write_text("new\n", encoding="utf-8")
    assert dirty_provenance(repo)["summary"]["untracked"] == 1
    projection = tmp_path / "projection"
    projection.mkdir()
    path = projection / ".cache/local-state/worktree/leases.json"
    path.parent.mkdir(parents=True)
    payload = {"leases": [{"subject": "work/landed"}, {"branch": "work/other"}]}
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert retirement_shared.delete_json_projection_lease(projection, subject="work/landed") == 1
    assert json.loads(path.read_text(encoding="utf-8"))["leases"] == [{"branch": "work/other"}]
