from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.surface.cli.root.planning as planning_cli
import ethos.surface.cli.root.proof as proof_cli
from ethos.repository.adoption.planner import adoption_plan
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked

if TYPE_CHECKING:
    from pathlib import Path


def test_valid_adopter_plan_and_prove_surface_lifecycle_gap(monkeypatch, tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, profile="generic", apply=True)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "adopt generic profile")
    gap = "openspec_claim_binding_missing:material-change"
    calls: list[tuple[Path, bool]] = []

    def report(root: Path, *, lifecycle: bool = False, **_kwargs: object) -> dict[str, object]:
        calls.append((root, lifecycle))
        return {"ok": False, "required_gaps": [gap]}

    monkeypatch.setattr(planning_cli, "openspec_governance_report", report)
    monkeypatch.setattr(proof_cli, "openspec_governance_report", report)
    plan = run_ethos("plan", "--root", repo.as_posix(), "--json")
    prove = run_ethos_blocked("prove", "--root", repo.as_posix(), "--json")

    assert plan["ok"] is False
    assert [plan["required_gaps"], prove["required_gaps"]] == [[gap], [gap]]
    assert calls == [(repo, True), (repo, True)]
