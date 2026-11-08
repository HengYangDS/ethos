"""`ethos hook retire-records` reports the retirement preview as one structured result."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import ethos.application.retention as retention
from ethos.adapters.store.state.schema import local_state_root
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import init_git_repo
from tests.support.retention_store import proof_check
from tests.support.retention_store import put

if TYPE_CHECKING:
    import pytest


def test_the_preview_reports_candidates_and_its_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The result counts candidates and bytes per kind and names the plan it wrote."""
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
    assert record.exists()
