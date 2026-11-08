"""`ethos hook retire-records` previews a plan and hands a person its destructive apply."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.application.retention as retention
from ethos.adapters.store.state.schema import local_state_root
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import init_git_repo
from tests.support.retention_store import proof_check
from tests.support.retention_store import put

if TYPE_CHECKING:
    import pytest


def test_the_preview_reports_candidates_and_its_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The preview counts candidates and names its plan; its apply needs `--authorize`."""
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    monkeypatch.setattr(retention, "runtime_selected", lambda _root: True)
    record = put(local_state_root(repo), "artifacts", proof_check(), ".json", age_days=30)

    result = run_ethos("hook", "retire-records", "--root", repo.as_posix(), "--json")

    assert result["verdict"] == "pass", result
    assert result["state"] == "planned"
    assert result["summary"]["candidates"] == {"proof-check": 1}
    assert result["summary"]["candidate_bytes"] == {"proof-check": record.stat().st_size}
    plan = result["data"]["plan"]
    assert Path(plan["path"]).name == f"{plan['sha256']}.json"
    assert result["user_decision_required"] is True
    assert (result["next"]["destructive"], result["next"]["authorization"]) == (True, "human")
    argv = shlex.split(result["next_action"])[1:]
    refused = run_ethos_blocked(*(word for word in argv if word != "--authorize"))
    assert refused["required_gaps"] == ["authorization_required"]
    assert record.exists()
    applied = run_ethos(*argv)
    assert (applied["state"], applied["summary"]["deleted"]) == ("applied", 1)
    assert not record.exists()
